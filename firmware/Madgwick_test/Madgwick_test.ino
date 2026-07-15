#include <Wire.h>
#include <math.h>
TwoWire &bus = Wire1;
const uint8_t ADDR=0x6B, CTRL1_XL=0x10, CTRL2_G=0x11, CTRL3_C=0x12, OUTX_L_A=0x28, OUTX_L_G=0x22;
const float ACC=0.061f/1000.0f, GYR=8.75f/1000.0f, DEG2RAD=0.0174533f;
const float beta = 0.1f;                       // Madgwick gain — the new "alpha"
float bx=0,by=0,bz=0;                          // gyro bias, all 3 axes (dps)
float q0=1,q1=0,q2=0,q3=0;                      // orientation quaternion
uint32_t tPrev;

void wr(uint8_t r,uint8_t v){bus.beginTransmission(ADDR);bus.write(r);bus.write(v);bus.endTransmission();}
void rdN(uint8_t r,uint8_t*b,uint8_t n){bus.beginTransmission(ADDR);bus.write(r);bus.endTransmission(false);
  bus.requestFrom(ADDR,n);for(uint8_t i=0;i<n&&bus.available();i++)b[i]=bus.read();}
int16_t le(uint8_t lo,uint8_t hi){return (int16_t)((hi<<8)|lo);}
float invSqrt(float x){return 1.0f/sqrtf(x);}

void readIMU(float&ax,float&ay,float&az,float&gx,float&gy,float&gz){
  uint8_t a[6],g[6]; rdN(OUTX_L_A,a,6); rdN(OUTX_L_G,g,6);
  ax=le(a[0],a[1])*ACC; ay=le(a[2],a[3])*ACC; az=le(a[4],a[5])*ACC;
  gx=le(g[0],g[1])*GYR; gy=le(g[2],g[3])*GYR; gz=le(g[4],g[5])*GYR;
}

void madgwick(float ax,float ay,float az,float gx,float gy,float gz,float dt){
  float qD1,qD2,qD3,qD4,s0,s1,s2,s3,rn;
  qD1=0.5f*(-q1*gx-q2*gy-q3*gz);               // gyro -> quaternion rate
  qD2=0.5f*( q0*gx+q2*gz-q3*gy);
  qD3=0.5f*( q0*gy-q1*gz+q3*gx);
  qD4=0.5f*( q0*gz+q1*gy-q2*gx);
  if(!(ax==0&&ay==0&&az==0)){
    rn=invSqrt(ax*ax+ay*ay+az*az); ax*=rn; ay*=rn; az*=rn;   // normalize accel
    float _2q0=2*q0,_2q1=2*q1,_2q2=2*q2,_2q3=2*q3,_4q0=4*q0,_4q1=4*q1,_4q2=4*q2,_8q1=8*q1,_8q2=8*q2;
    float q0q0=q0*q0,q1q1=q1*q1,q2q2=q2*q2,q3q3=q3*q3;
    s0=_4q0*q2q2+_2q2*ax+_4q0*q1q1-_2q1*ay;     // gradient-descent step toward gravity
    s1=_4q1*q3q3-_2q3*ax+4*q0q0*q1-_2q0*ay-_4q1+_8q1*q1q1+_8q1*q2q2+_4q1*az;
    s2=4*q0q0*q2+_2q0*ax+_4q2*q3q3-_2q3*ay-_4q2+_8q2*q1q1+_8q2*q2q2+_4q2*az;
    s3=4*q1q1*q3-_2q1*ax+4*q2q2*q3-_2q2*ay;
    rn=invSqrt(s0*s0+s1*s1+s2*s2+s3*s3); s0*=rn;s1*=rn;s2*=rn;s3*=rn;
    qD1-=beta*s0; qD2-=beta*s1; qD3-=beta*s2; qD4-=beta*s3;  // blend correction in
  }
  q0+=qD1*dt; q1+=qD2*dt; q2+=qD3*dt; q3+=qD4*dt;
  rn=invSqrt(q0*q0+q1*q1+q2*q2+q3*q3); q0*=rn;q1*=rn;q2*=rn;q3*=rn;
}

void setup(){
  Serial.begin(115200); while(!Serial && millis()<3000);
  bus.begin(); bus.setClock(400000);
  wr(CTRL3_C,0x44); wr(CTRL1_XL,0x40); wr(CTRL2_G,0x40); delay(100);
  double sx=0,sy=0,sz=0;                        // calibrate all 3 gyro axes
  for(int i=0;i<2000;i++){float ax,ay,az,gx,gy,gz; readIMU(ax,ay,az,gx,gy,gz); sx+=gx;sy+=gy;sz+=gz; delay(2);}
  bx=sx/2000; by=sy/2000; bz=sz/2000;
  tPrev=micros();
}

void loop(){
  float ax,ay,az,gx,gy,gz; readIMU(ax,ay,az,gx,gy,gz);
  gx=(gx-bx)*DEG2RAD; gy=(gy-by)*DEG2RAD; gz=(gz-bz)*DEG2RAD;   // de-bias, dps -> rad/s
  uint32_t now=micros(); float dt=(now-tPrev)*1e-6f; tPrev=now;
  madgwick(ax,ay,az,gx,gy,gz,dt);
  float t=2*(q0*q2-q3*q1); if(t>1)t=1; if(t<-1)t=-1;            // clamp to avoid asin NaN
  float roll =atan2f(2*(q0*q1+q2*q3),1-2*(q1*q1+q2*q2))*57.2958f;
  float pitch=asinf(t)*57.2958f;
  float yaw  =atan2f(2*(q0*q3+q1*q2),1-2*(q2*q2+q3*q3))*57.2958f;
  Serial.print("roll:");  Serial.print(roll,1);
  Serial.print(" pitch:");Serial.print(pitch,1);
  Serial.print(" yaw:");  Serial.println(yaw,1);
  delay(10);
}