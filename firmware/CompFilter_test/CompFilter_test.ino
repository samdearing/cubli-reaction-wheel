#include <Wire.h>
#include <math.h>
TwoWire &bus = Wire1;
const uint8_t ADDR=0x6B, CTRL1_XL=0x10, CTRL2_G=0x11, CTRL3_C=0x12, OUTX_L_A=0x28, OUTX_L_G=0x22;
const float ACC=0.061f/1000.0f, GYR=8.75f/1000.0f, ALPHA=0.98f;
float gyBias=0, theta=0; uint32_t tPrev;

void wr(uint8_t r,uint8_t v){bus.beginTransmission(ADDR);bus.write(r);bus.write(v);bus.endTransmission();}
void rdN(uint8_t r,uint8_t*b,uint8_t n){bus.beginTransmission(ADDR);bus.write(r);bus.endTransmission(false);
  bus.requestFrom(ADDR,n);for(uint8_t i=0;i<n&&bus.available();i++)b[i]=bus.read();}
int16_t le(uint8_t lo,uint8_t hi){return (int16_t)((hi<<8)|lo);}

void setup(){
  Serial.begin(115200); while(!Serial && millis()<3000);
  bus.begin(); bus.setClock(400000);
  wr(CTRL3_C,0x44); wr(CTRL1_XL,0x40); wr(CTRL2_G,0x40); delay(100);
  double s=0; for(int i=0;i<2000;i++){uint8_t g[6];rdN(OUTX_L_G,g,6);s+=le(g[2],g[3])*GYR;delay(2);} gyBias=s/2000;
  uint8_t a[6]; rdN(OUTX_L_A,a,6);
  theta=atan2(le(a[0],a[1])*ACC, le(a[4],a[5])*ACC)*180.0/PI;   // seed with accel angle
  tPrev=micros();
}

void loop(){
  uint8_t a[6],g[6]; rdN(OUTX_L_A,a,6); rdN(OUTX_L_G,g,6);
  float ax=le(a[0],a[1])*ACC, az=le(a[4],a[5])*ACC;
  float gy=le(g[2],g[3])*GYR - gyBias;                 // de-biased rate
  uint32_t now=micros(); float dt=(now-tPrev)*1e-6f; tPrev=now;
  float accAngle = atan2(ax,az)*180.0/PI;              // absolute tilt
  theta = ALPHA*(theta + gy*dt) + (1.0f-ALPHA)*accAngle;   // <-- the complementary filter
  Serial.print("accel="); Serial.print(accAngle,1);
  Serial.print("  fused="); Serial.println(theta,1);
}