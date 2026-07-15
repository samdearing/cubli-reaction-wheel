#include <Wire.h>
TwoWire &bus = Wire1;            // IMU is on Wire1 (16/17)
const uint8_t ADDR = 0x6B;

const uint8_t WHO_AM_I = 0x0F, CTRL1_XL = 0x10, CTRL2_G = 0x11, CTRL3_C = 0x12;
const uint8_t OUTX_L_A = 0x28, OUTX_L_G = 0x22;
const float ACC = 0.061f/1000.0f;   // ±2g  → g per LSB
const float GYR = 8.75f /1000.0f;   // ±250 dps → dps per LSB

void wr(uint8_t r, uint8_t v){ bus.beginTransmission(ADDR); bus.write(r); bus.write(v); bus.endTransmission(); }
uint8_t rd(uint8_t r){ bus.beginTransmission(ADDR); bus.write(r); bus.endTransmission(false);
  bus.requestFrom(ADDR,(uint8_t)1); return bus.read(); }
void rdN(uint8_t r, uint8_t*b, uint8_t n){ bus.beginTransmission(ADDR); bus.write(r); bus.endTransmission(false);
  bus.requestFrom(ADDR,n); for(uint8_t i=0;i<n && bus.available();i++) b[i]=bus.read(); }
int16_t le(uint8_t lo,uint8_t hi){ return (int16_t)((hi<<8)|lo); }

void setup(){
  Serial.begin(115200); while(!Serial && millis()<3000);
  bus.begin(); bus.setClock(400000);
  uint8_t id = rd(WHO_AM_I);
  Serial.print("WHO_AM_I = 0x"); Serial.println(id, HEX);   // expect 0x6B
  if(id != 0x6B){ Serial.println("bad ID - stop"); while(1); }
  wr(CTRL3_C, 0x44);   // BDU + auto-increment
  wr(CTRL1_XL, 0x40);  // accel 104 Hz, ±2 g
  wr(CTRL2_G,  0x40);  // gyro  104 Hz, ±250 dps
  Serial.println("Hold still and watch:");
}

void loop(){
  uint8_t a[6], g[6];
  rdN(OUTX_L_A, a, 6); rdN(OUTX_L_G, g, 6);
  float ax=le(a[0],a[1])*ACC, ay=le(a[2],a[3])*ACC, az=le(a[4],a[5])*ACC;
  float gx=le(g[0],g[1])*GYR, gy=le(g[2],g[3])*GYR, gz=le(g[4],g[5])*GYR;
  Serial.print("A[g] "); Serial.print(ax,3); Serial.print(" "); Serial.print(ay,3); Serial.print(" "); Serial.print(az,3);
  Serial.print("  |a|="); Serial.print(sqrt(ax*ax+ay*ay+az*az),3);
  Serial.print("   G[dps] "); Serial.print(gx,1); Serial.print(" "); Serial.print(gy,1); Serial.print(" "); Serial.println(gz,1);
  delay(50);
}