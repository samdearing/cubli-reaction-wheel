#include <Wire.h>
TwoWire &bus = Wire1;
const uint8_t ADDR = 0x6B;
const uint8_t CTRL1_XL=0x10, CTRL2_G=0x11, CTRL3_C=0x12, OUTX_L_G=0x22;
const float GYR = 8.75f/1000.0f;          // ±250 dps -> dps/LSB

float gxBias=0, gyBias=0, gzBias=0;        // <-- the numbers we solve for

void wr(uint8_t r,uint8_t v){bus.beginTransmission(ADDR);bus.write(r);bus.write(v);bus.endTransmission();}
void rdN(uint8_t r,uint8_t*b,uint8_t n){bus.beginTransmission(ADDR);bus.write(r);bus.endTransmission(false);
  bus.requestFrom(ADDR,n);for(uint8_t i=0;i<n&&bus.available();i++)b[i]=bus.read();}
int16_t le(uint8_t lo,uint8_t hi){return (int16_t)((hi<<8)|lo);}

void readGyro(float&x,float&y,float&z){
  uint8_t g[6]; rdN(OUTX_L_G,g,6);
  x=le(g[0],g[1])*GYR; y=le(g[2],g[3])*GYR; z=le(g[4],g[5])*GYR;
}

void calibrateGyro(uint16_t n=2000){            // <-- NEW
  Serial.println("Calibrating gyro - HOLD STILL...");
  double sx=0,sy=0,sz=0;
  for(uint16_t i=0;i<n;i++){ float x,y,z; readGyro(x,y,z); sx+=x; sy+=y; sz+=z; delay(2); }
  gxBias=sx/n; gyBias=sy/n; gzBias=sz/n;        // average = the DC bias
  Serial.print("Bias [dps] x="); Serial.print(gxBias,3);
  Serial.print(" y="); Serial.print(gyBias,3); Serial.print(" z="); Serial.println(gzBias,3);
}

void setup(){
  Serial.begin(115200); while(!Serial && millis()<3000);
  bus.begin(); bus.setClock(400000);
  wr(CTRL3_C,0x44); wr(CTRL2_G,0x40);           // BDU+auto-inc; gyro 104 Hz, ±250 dps
  delay(100);
  calibrateGyro();
}

void loop(){
  float gx,gy,gz; readGyro(gx,gy,gz);
  gx-=gxBias; gy-=gyBias; gz-=gzBias;           // <-- subtract the bias
  Serial.print("G corrected [dps] x="); Serial.print(gx,2);
  Serial.print(" y="); Serial.print(gy,2); Serial.print(" z="); Serial.println(gz,2);
  delay(50);
}