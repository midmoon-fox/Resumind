import{d as ae,o as Ue,a as Le,w as ne,b as C,c as k,n as ve,e as U,r as Pe,_ as he,F as nt,f as at,g as st,t as ut,h as ct,u as O,i as _e,j as we,k as H,l as me,m as Ae,p as lt,q as ft,S as dt,A as be,R as Fe}from"./index-BiFPjb6c.js";const mt=ae({__name:"ParticlesBg",props:{color:{},quantity:{default:92},staticity:{default:18},ease:{default:10},class:{default:""}},setup(Y){const u=Y,h=Pe(null);let p=null,L=[],s=0,E=0,B=1,d=0,Q=0,W=0,S=!1,m=0;function Z(a){return`rgba(${m>>16&255}, ${m>>8&255}, ${m&255}, ${a})`}function t(){return{x:Math.random()*s,y:Math.random()*E,tx:0,ty:0,size:Math.random()*1.5+.7,alpha:0,targetAlpha:Math.random()*.45+.12,dx:(Math.random()-.5)*.18,dy:(Math.random()-.5)*.18,magnetism:.3+Math.random()*2.2}}function g(){if(!h.value||!p)return;const R=(u.color??getComputedStyle(h.value).getPropertyValue("--color-accent")).trim().replace("#",""),$=R.length===3?[...R].map(I=>I+I).join(""):R;m=Number.parseInt($,16);const x=h.value.getBoundingClientRect();s=x.width,E=x.height,B=Math.min(window.devicePixelRatio||1,2),h.value.width=Math.round(s*B),h.value.height=Math.round(E*B),p.setTransform(B,0,0,B,0,0),L=Array.from({length:u.quantity},t)}function ee(a){if(!h.value)return;const R=h.value.getBoundingClientRect();S=a.clientX>=R.left&&a.clientX<=R.right&&a.clientY>=R.top&&a.clientY<=R.bottom,Q=a.clientX-R.left-s/2,W=a.clientY-R.top-E/2}function w(){if(p){p.clearRect(0,0,s,E);for(const a of L){const R=Math.min(a.x,s-a.x,a.y,E-a.y),$=Math.min(1,Math.max(0,R/20));a.alpha+=(a.targetAlpha*$-a.alpha)*.08,a.x+=a.dx,a.y+=a.dy;const x=S?Q/(u.staticity/a.magnetism):0,I=S?W/(u.staticity/a.magnetism):0;a.tx+=(x-a.tx)/Math.max(1,u.ease),a.ty+=(I-a.ty)/Math.max(1,u.ease),(a.x<-a.size||a.x>s+a.size||a.y<-a.size||a.y>E+a.size)&&Object.assign(a,t()),p.beginPath(),p.arc(a.x+a.tx,a.y+a.ty,a.size,0,Math.PI*2),p.fillStyle=Z(a.alpha),p.fill()}d=requestAnimationFrame(w)}}return Ue(()=>{p=h.value?.getContext("2d",{alpha:!0})??null,g(),window.addEventListener("resize",g),window.addEventListener("pointermove",ee,{passive:!0}),d=requestAnimationFrame(w)}),Le(()=>{cancelAnimationFrame(d),window.removeEventListener("resize",g),window.removeEventListener("pointermove",ee)}),ne(()=>[u.quantity,u.color],g),(a,R)=>(C(),k("div",{class:ve(u.class),"aria-hidden":"true"},[U("canvas",{ref_key:"canvas",ref:h,class:"particles-canvas"},null,512)],2))}}),vt=he(mt,[["__scopeId","data-v-39e18ead"]]),ht=["aria-label"],pt=ae({__name:"BreathingText",props:{text:{},class:{default:""},staggerDuration:{default:.075}},setup(Y){const u=Y,h=ct(()=>[...u.text]);return(p,L)=>(C(),k("h1",{class:ve(["breathing-text",u.class]),"aria-label":u.text},[(C(!0),k(nt,null,at(h.value,(s,E)=>(C(),k("span",{key:`${E}-${s}`,class:"breathing-letter","aria-hidden":"true",style:st({"--delay":`${E*u.staggerDuration}s`})},ut(s===" "?" ":s),5))),128))],10,ht))}}),xt=he(pt,[["__scopeId","data-v-06168189"]]),gt=ae({__name:"FluidCursor",props:{simResolution:{default:128},dyeResolution:{default:1440},captureResolution:{default:512},densityDissipation:{default:3.5},velocityDissipation:{default:2},pressure:{default:.1},pressureIterations:{default:20},curl:{default:3},splatRadius:{default:.2},splatForce:{default:6e3},shading:{type:Boolean,default:!0},colorUpdateSpeed:{default:10},backColor:{default:()=>({r:0,g:0,b:0})},transparent:{type:Boolean,default:!0},class:{type:[Boolean,null,String,Object,Array]}},setup(Y){const u=Y;function h(){return{id:-1,texcoordX:0,texcoordY:0,prevTexcoordX:0,prevTexcoordY:0,deltaX:0,deltaY:0,down:!1,moved:!1,color:{r:0,g:0,b:0}}}const p=Pe(null);let L;return Le(()=>L?.()),Ue(()=>{const s=new AbortController;let E=!0,B=0;L=()=>{E=!1,cancelAnimationFrame(B),s.abort()};const d=p.value;if(!d)return;const Q=getComputedStyle(d),W=["--color-accent","--color-accent-hover","--color-accent-border"].map(e=>{const r=Number.parseInt(Q.getPropertyValue(e).trim().slice(1),16);return{r:(r>>16&255)/255,g:(r>>8&255)/255,b:(r&255)/255}}),S=[h()],m={SIM_RESOLUTION:u.simResolution,DYE_RESOLUTION:u.dyeResolution,CAPTURE_RESOLUTION:u.captureResolution,DENSITY_DISSIPATION:u.densityDissipation,VELOCITY_DISSIPATION:u.velocityDissipation,PRESSURE:u.pressure,PRESSURE_ITERATIONS:u.pressureIterations,CURL:u.curl,SPLAT_RADIUS:u.splatRadius,SPLAT_FORCE:u.splatForce,SHADING:u.shading,COLOR_UPDATE_SPEED:u.colorUpdateSpeed,BACK_COLOR:u.backColor,TRANSPARENT:u.transparent};let Z;try{Z=ee(d)}catch{return}const{gl:t,ext:g}=Z;if(!t||!g)return;g.supportLinearFiltering||(m.DYE_RESOLUTION=256,m.SHADING=!1);function ee(e){const r={alpha:!0,depth:!1,stencil:!1,antialias:!1,preserveDrawingBuffer:!1};let i=e.getContext("webgl2",r);if(i||(i=e.getContext("webgl",r)||e.getContext("experimental-webgl",r)),!i)throw new Error("Unable to initialize WebGL.");const o="drawBuffers"in i;let n=!1,c=null;o?(i.getExtension("EXT_color_buffer_float"),n=!!i.getExtension("OES_texture_float_linear")):(c=i.getExtension("OES_texture_half_float"),n=!!i.getExtension("OES_texture_half_float_linear")),i.clearColor(0,0,0,1);const f=o?i.HALF_FLOAT:c&&c.HALF_FLOAT_OES||0;let b=null,N=null,J=null;return o?(b=w(i,i.RGBA16F,i.RGBA,f),N=w(i,i.RG16F,i.RG,f),J=w(i,i.R16F,i.RED,f)):(b=w(i,i.RGBA,i.RGBA,f),N=w(i,i.RGBA,i.RGBA,f),J=w(i,i.RGBA,i.RGBA,f)),{gl:i,ext:{formatRGBA:b,formatRG:N,formatR:J,halfFloatTexType:f,supportLinearFiltering:n}}}function w(e,r,i,o){if(!a(e,r,i,o)){if("drawBuffers"in e){const n=e;switch(r){case n.R16F:return w(n,n.RG16F,n.RG,o);case n.RG16F:return w(n,n.RGBA16F,n.RGBA,o);default:return null}}return null}return{internalFormat:r,format:i}}function a(e,r,i,o){const n=e.createTexture();if(!n)return!1;e.bindTexture(e.TEXTURE_2D,n),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MIN_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MAG_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_S,e.CLAMP_TO_EDGE),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_T,e.CLAMP_TO_EDGE),e.texImage2D(e.TEXTURE_2D,0,r,4,4,0,i,o,null);const c=e.createFramebuffer();return c?(e.bindFramebuffer(e.FRAMEBUFFER,c),e.framebufferTexture2D(e.FRAMEBUFFER,e.COLOR_ATTACHMENT0,e.TEXTURE_2D,n,0),e.checkFramebufferStatus(e.FRAMEBUFFER)===e.FRAMEBUFFER_COMPLETE):!1}function R(e){if(!e.length)return 0;let r=0;for(let i=0;i<e.length;i++)r=(r<<5)-r+e.charCodeAt(i),r|=0;return r}function $(e,r){if(!r)return e;let i="";for(const o of r)i+=`#define ${o}
`;return i+e}function x(e,r,i=null){const o=$(r,i),n=t.createShader(e);return n?(t.shaderSource(n,o),t.compileShader(n),n):null}function I(e,r){if(!e||!r)return null;const i=t.createProgram();return i?(t.attachShader(i,e),t.attachShader(i,r),t.linkProgram(i),i):null}function pe(e){const r={},i=t.getProgramParameter(e,t.ACTIVE_UNIFORMS);for(let o=0;o<i;o++){const n=t.getActiveUniform(e,o);n&&(r[n.name]=t.getUniformLocation(e,n.name))}return r}class P{program;uniforms;constructor(r,i){this.program=I(r,i),this.uniforms=this.program?pe(this.program):{}}bind(){this.program&&t.useProgram(this.program)}}class Be{vertexShader;fragmentShaderSource;programs;activeProgram;uniforms;constructor(r,i){this.vertexShader=r,this.fragmentShaderSource=i,this.programs={},this.activeProgram=null,this.uniforms={}}setKeywords(r){let i=0;for(const n of r)i+=R(n);let o=this.programs[i];if(o==null){const n=x(t.FRAGMENT_SHADER,this.fragmentShaderSource,r);o=I(this.vertexShader,n),this.programs[i]=o}o!==this.activeProgram&&(o&&(this.uniforms=pe(o)),this.activeProgram=o)}bind(){this.activeProgram&&t.useProgram(this.activeProgram)}}const F=x(t.VERTEX_SHADER,`
        precision highp float;
        attribute vec2 aPosition;
        varying vec2 vUv;
        varying vec2 vL;
        varying vec2 vR;
        varying vec2 vT;
        varying vec2 vB;
        uniform vec2 texelSize;

        void main () {
          vUv = aPosition * 0.5 + 0.5;
          vL = vUv - vec2(texelSize.x, 0.0);
          vR = vUv + vec2(texelSize.x, 0.0);
          vT = vUv + vec2(0.0, texelSize.y);
          vB = vUv - vec2(0.0, texelSize.y);
          gl_Position = vec4(aPosition, 0.0, 1.0);
        }
      `),ze=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        uniform sampler2D uTexture;

        void main () {
          gl_FragColor = texture2D(uTexture, vUv);
        }
      `),Ce=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        uniform sampler2D uTexture;
        uniform float value;

        void main () {
          gl_FragColor = value * texture2D(uTexture, vUv);
        }
      `),Ie=`
        precision highp float;
        precision highp sampler2D;
        varying vec2 vUv;
        varying vec2 vL;
        varying vec2 vR;
        varying vec2 vT;
        varying vec2 vB;
        uniform sampler2D uTexture;
        uniform sampler2D uDithering;
        uniform vec2 ditherScale;
        uniform vec2 texelSize;

        vec3 linearToGamma (vec3 color) {
          color = max(color, vec3(0));
          return max(1.055 * pow(color, vec3(0.416666667)) - 0.055, vec3(0));
        }

        void main () {
          vec3 c = texture2D(uTexture, vUv).rgb;
          #ifdef SHADING
            vec3 lc = texture2D(uTexture, vL).rgb;
            vec3 rc = texture2D(uTexture, vR).rgb;
            vec3 tc = texture2D(uTexture, vT).rgb;
            vec3 bc = texture2D(uTexture, vB).rgb;

            float dx = length(rc) - length(lc);
            float dy = length(tc) - length(bc);

            vec3 n = normalize(vec3(dx, dy, length(texelSize)));
            vec3 l = vec3(0.0, 0.0, 1.0);

            float diffuse = clamp(dot(n, l) + 0.7, 0.7, 1.0);
            c *= diffuse;
          #endif

          float a = max(c.r, max(c.g, c.b));
          gl_FragColor = vec4(c, a);
        }
      `,Me=x(t.FRAGMENT_SHADER,`
        precision highp float;
        precision highp sampler2D;
        varying vec2 vUv;
        uniform sampler2D uTarget;
        uniform float aspectRatio;
        uniform vec3 color;
        uniform vec2 point;
        uniform float radius;

        void main () {
          vec2 p = vUv - point.xy;
          p.x *= aspectRatio;
          vec3 splat = exp(-dot(p, p) / radius) * color;
          vec3 base = texture2D(uTarget, vUv).xyz;
          gl_FragColor = vec4(base + splat, 1.0);
        }
      `),Xe=x(t.FRAGMENT_SHADER,`
        precision highp float;
        precision highp sampler2D;
        varying vec2 vUv;
        uniform sampler2D uVelocity;
        uniform sampler2D uSource;
        uniform vec2 texelSize;
        uniform vec2 dyeTexelSize;
        uniform float dt;
        uniform float dissipation;

        vec4 bilerp (sampler2D sam, vec2 uv, vec2 tsize) {
          vec2 st = uv / tsize - 0.5;
          vec2 iuv = floor(st);
          vec2 fuv = fract(st);

          vec4 a = texture2D(sam, (iuv + vec2(0.5, 0.5)) * tsize);
          vec4 b = texture2D(sam, (iuv + vec2(1.5, 0.5)) * tsize);
          vec4 c = texture2D(sam, (iuv + vec2(0.5, 1.5)) * tsize);
          vec4 d = texture2D(sam, (iuv + vec2(1.5, 1.5)) * tsize);

          return mix(mix(a, b, fuv.x), mix(c, d, fuv.x), fuv.y);
        }

        void main () {
          #ifdef MANUAL_FILTERING
            vec2 coord = vUv - dt * bilerp(uVelocity, vUv, texelSize).xy * texelSize;
            vec4 result = bilerp(uSource, coord, dyeTexelSize);
          #else
            vec2 coord = vUv - dt * texture2D(uVelocity, vUv).xy * texelSize;
            vec4 result = texture2D(uSource, coord);
          #endif
          float decay = 1.0 + dissipation * dt;
          gl_FragColor = result / decay;
        }
      `,g.supportLinearFiltering?null:["MANUAL_FILTERING"]),Ne=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        varying highp vec2 vL;
        varying highp vec2 vR;
        varying highp vec2 vT;
        varying highp vec2 vB;
        uniform sampler2D uVelocity;

        void main () {
          float L = texture2D(uVelocity, vL).x;
          float R = texture2D(uVelocity, vR).x;
          float T = texture2D(uVelocity, vT).y;
          float B = texture2D(uVelocity, vB).y;

          vec2 C = texture2D(uVelocity, vUv).xy;
          if (vL.x < 0.0) { L = -C.x; }
          if (vR.x > 1.0) { R = -C.x; }
          if (vT.y > 1.0) { T = -C.y; }
          if (vB.y < 0.0) { B = -C.y; }

          float div = 0.5 * (R - L + T - B);
          gl_FragColor = vec4(div, 0.0, 0.0, 1.0);
        }
      `),Oe=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        varying highp vec2 vL;
        varying highp vec2 vR;
        varying highp vec2 vT;
        varying highp vec2 vB;
        uniform sampler2D uVelocity;

        void main () {
          float L = texture2D(uVelocity, vL).y;
          float R = texture2D(uVelocity, vR).y;
          float T = texture2D(uVelocity, vT).x;
          float B = texture2D(uVelocity, vB).x;
          float vorticity = R - L - T + B;
          gl_FragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
        }
      `),Ye=x(t.FRAGMENT_SHADER,`
        precision highp float;
        precision highp sampler2D;
        varying vec2 vUv;
        varying vec2 vL;
        varying vec2 vR;
        varying vec2 vT;
        varying vec2 vB;
        uniform sampler2D uVelocity;
        uniform sampler2D uCurl;
        uniform float curl;
        uniform float dt;

        void main () {
          float L = texture2D(uCurl, vL).x;
          float R = texture2D(uCurl, vR).x;
          float T = texture2D(uCurl, vT).x;
          float B = texture2D(uCurl, vB).x;
          float C = texture2D(uCurl, vUv).x;

          vec2 force = 0.5 * vec2(abs(T) - abs(B), abs(R) - abs(L));
          force /= length(force) + 0.0001;
          force *= curl * C;
          force.y *= -1.0;

          vec2 velocity = texture2D(uVelocity, vUv).xy;
          velocity += force * dt;
          velocity = min(max(velocity, -1000.0), 1000.0);
          gl_FragColor = vec4(velocity, 0.0, 1.0);
        }
      `),Ge=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        varying highp vec2 vL;
        varying highp vec2 vR;
        varying highp vec2 vT;
        varying highp vec2 vB;
        uniform sampler2D uPressure;
        uniform sampler2D uDivergence;

        void main () {
          float L = texture2D(uPressure, vL).x;
          float R = texture2D(uPressure, vR).x;
          float T = texture2D(uPressure, vT).x;
          float B = texture2D(uPressure, vB).x;
          float C = texture2D(uPressure, vUv).x;
          float divergence = texture2D(uDivergence, vUv).x;
          float pressure = (L + R + B + T - divergence) * 0.25;
          gl_FragColor = vec4(pressure, 0.0, 0.0, 1.0);
        }
      `),Ve=x(t.FRAGMENT_SHADER,`
        precision mediump float;
        precision mediump sampler2D;
        varying highp vec2 vUv;
        varying highp vec2 vL;
        varying highp vec2 vR;
        varying highp vec2 vT;
        varying highp vec2 vB;
        uniform sampler2D uPressure;
        uniform sampler2D uVelocity;

        void main () {
          float L = texture2D(uPressure, vL).x;
          float R = texture2D(uPressure, vR).x;
          float T = texture2D(uPressure, vT).x;
          float B = texture2D(uPressure, vB).x;
          vec2 velocity = texture2D(uVelocity, vUv).xy;
          velocity.xy -= vec2(R - L, T - B);
          gl_FragColor = vec4(velocity, 0.0, 1.0);
        }
      `),_=(()=>{const e=t.createBuffer();t.bindBuffer(t.ARRAY_BUFFER,e),t.bufferData(t.ARRAY_BUFFER,new Float32Array([-1,-1,-1,1,1,1,1,-1]),t.STATIC_DRAW);const r=t.createBuffer();return t.bindBuffer(t.ELEMENT_ARRAY_BUFFER,r),t.bufferData(t.ELEMENT_ARRAY_BUFFER,new Uint16Array([0,1,2,0,2,3]),t.STATIC_DRAW),t.vertexAttribPointer(0,2,t.FLOAT,!1,0,0),t.enableVertexAttribArray(0),(i,o=!1)=>{t&&(i?(t.viewport(0,0,i.width,i.height),t.bindFramebuffer(t.FRAMEBUFFER,i.fbo)):(t.viewport(0,0,t.drawingBufferWidth,t.drawingBufferHeight),t.bindFramebuffer(t.FRAMEBUFFER,null)),o&&(t.clearColor(0,0,0,1),t.clear(t.COLOR_BUFFER_BIT)),t.drawElements(t.TRIANGLES,6,t.UNSIGNED_SHORT,0))}})();let D,l,se,ue,z;const ce=new P(F,ze),q=new P(F,Ce),T=new P(F,Me),v=new P(F,Xe),K=new P(F,Ne),j=new P(F,Oe),A=new P(F,Ye),M=new P(F,Ge),X=new P(F,Ve),G=new Be(F,Ie);function V(e,r,i,o,n,c){t.activeTexture(t.TEXTURE0);const f=t.createTexture();t.bindTexture(t.TEXTURE_2D,f),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MIN_FILTER,c),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MAG_FILTER,c),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_WRAP_S,t.CLAMP_TO_EDGE),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_WRAP_T,t.CLAMP_TO_EDGE),t.texImage2D(t.TEXTURE_2D,0,i,e,r,0,o,n,null);const b=t.createFramebuffer();t.bindFramebuffer(t.FRAMEBUFFER,b),t.framebufferTexture2D(t.FRAMEBUFFER,t.COLOR_ATTACHMENT0,t.TEXTURE_2D,f,0),t.viewport(0,0,e,r),t.clear(t.COLOR_BUFFER_BIT);const N=1/e,J=1/r;return{texture:f,fbo:b,width:e,height:r,texelSizeX:N,texelSizeY:J,attach(De){return t.activeTexture(t.TEXTURE0+De),t.bindTexture(t.TEXTURE_2D,f),De}}}function le(e,r,i,o,n,c){const f=V(e,r,i,o,n,c),b=V(e,r,i,o,n,c);return{width:e,height:r,texelSizeX:f.texelSizeX,texelSizeY:f.texelSizeY,read:f,write:b,swap(){const N=this.read;this.read=this.write,this.write=N}}}function He(e,r,i,o,n,c,f){const b=V(r,i,o,n,c,f);return ce.bind(),ce.uniforms.uTexture&&t.uniform1i(ce.uniforms.uTexture,e.attach(0)),_(b,!1),b}function xe(e,r,i,o,n,c,f){return e.width===r&&e.height===i||(e.read=He(e.read,r,i,o,n,c,f),e.write=V(r,i,o,n,c,f),e.width=r,e.height=i,e.texelSizeX=1/r,e.texelSizeY=1/i),e}function te(){const e=Re(m.SIM_RESOLUTION),r=Re(m.DYE_RESOLUTION),i=g.halfFloatTexType,o=g.formatRGBA,n=g.formatRG,c=g.formatR;if(!o||!n||!c)return;const f=g.supportLinearFiltering?t.LINEAR:t.NEAREST;t.disable(t.BLEND),D?D=xe(D,r.width,r.height,o.internalFormat,o.format,i,f):D=le(r.width,r.height,o.internalFormat,o.format,i,f),l?l=xe(l,e.width,e.height,n.internalFormat,n.format,i,f):l=le(e.width,e.height,n.internalFormat,n.format,i,f),se=V(e.width,e.height,c.internalFormat,c.format,i,t.NEAREST),ue=V(e.width,e.height,c.internalFormat,c.format,i,t.NEAREST),z=le(e.width,e.height,c.internalFormat,c.format,i,t.NEAREST)}function ge(){const e=[];m.SHADING&&e.push("SHADING"),G.setKeywords(e)}function Re(e){const r=t.drawingBufferWidth,i=t.drawingBufferHeight,o=r/i,n=o<1?1/o:o,c=Math.round(e),f=Math.round(e*n);return r>i?{width:f,height:c}:{width:c,height:f}}function y(e){const r=window.devicePixelRatio||1;return Math.floor(e*r)}ge(),te();let Te=Date.now(),re=0;function ie(){if(!E)return;const e=ke();We()&&te(),$e(e),qe(),Ke(e),je(null),B=requestAnimationFrame(ie)}function ke(){const e=Date.now();let r=(e-Te)/1e3;return r=Math.min(r,.016666),Te=e,r}function We(){const e=y(d.clientWidth),r=y(d.clientHeight);return d.width!==e||d.height!==r?(d.width=e,d.height=r,!0):!1}function $e(e){re+=e*m.COLOR_UPDATE_SPEED,re>=1&&(re=ot(re,0,1),S.forEach(r=>{r.color=oe()}))}function qe(){for(const e of S)e.moved&&(e.moved=!1,Qe(e))}function Ke(e){t.disable(t.BLEND),j.bind(),j.uniforms.texelSize&&t.uniform2f(j.uniforms.texelSize,l.texelSizeX,l.texelSizeY),j.uniforms.uVelocity&&t.uniform1i(j.uniforms.uVelocity,l.read.attach(0)),_(ue),A.bind(),A.uniforms.texelSize&&t.uniform2f(A.uniforms.texelSize,l.texelSizeX,l.texelSizeY),A.uniforms.uVelocity&&t.uniform1i(A.uniforms.uVelocity,l.read.attach(0)),A.uniforms.uCurl&&t.uniform1i(A.uniforms.uCurl,ue.attach(1)),A.uniforms.curl&&t.uniform1f(A.uniforms.curl,m.CURL),A.uniforms.dt&&t.uniform1f(A.uniforms.dt,e),_(l.write),l.swap(),K.bind(),K.uniforms.texelSize&&t.uniform2f(K.uniforms.texelSize,l.texelSizeX,l.texelSizeY),K.uniforms.uVelocity&&t.uniform1i(K.uniforms.uVelocity,l.read.attach(0)),_(se),q.bind(),q.uniforms.uTexture&&t.uniform1i(q.uniforms.uTexture,z.read.attach(0)),q.uniforms.value&&t.uniform1f(q.uniforms.value,m.PRESSURE),_(z.write),z.swap(),M.bind(),M.uniforms.texelSize&&t.uniform2f(M.uniforms.texelSize,l.texelSizeX,l.texelSizeY),M.uniforms.uDivergence&&t.uniform1i(M.uniforms.uDivergence,se.attach(0));for(let i=0;i<m.PRESSURE_ITERATIONS;i++)M.uniforms.uPressure&&t.uniform1i(M.uniforms.uPressure,z.read.attach(1)),_(z.write),z.swap();X.bind(),X.uniforms.texelSize&&t.uniform2f(X.uniforms.texelSize,l.texelSizeX,l.texelSizeY),X.uniforms.uPressure&&t.uniform1i(X.uniforms.uPressure,z.read.attach(0)),X.uniforms.uVelocity&&t.uniform1i(X.uniforms.uVelocity,l.read.attach(1)),_(l.write),l.swap(),v.bind(),v.uniforms.texelSize&&t.uniform2f(v.uniforms.texelSize,l.texelSizeX,l.texelSizeY),!g.supportLinearFiltering&&v.uniforms.dyeTexelSize&&t.uniform2f(v.uniforms.dyeTexelSize,l.texelSizeX,l.texelSizeY);const r=l.read.attach(0);v.uniforms.uVelocity&&t.uniform1i(v.uniforms.uVelocity,r),v.uniforms.uSource&&t.uniform1i(v.uniforms.uSource,r),v.uniforms.dt&&t.uniform1f(v.uniforms.dt,e),v.uniforms.dissipation&&t.uniform1f(v.uniforms.dissipation,m.VELOCITY_DISSIPATION),_(l.write),l.swap(),!g.supportLinearFiltering&&v.uniforms.dyeTexelSize&&t.uniform2f(v.uniforms.dyeTexelSize,D.texelSizeX,D.texelSizeY),v.uniforms.uVelocity&&t.uniform1i(v.uniforms.uVelocity,l.read.attach(0)),v.uniforms.uSource&&t.uniform1i(v.uniforms.uSource,D.read.attach(1)),v.uniforms.dissipation&&t.uniform1f(v.uniforms.dissipation,m.DENSITY_DISSIPATION),_(D.write),D.swap()}function je(e){t.blendFunc(t.ONE,t.ONE_MINUS_SRC_ALPHA),t.enable(t.BLEND),Je(e)}function Je(e){const r=t.drawingBufferWidth,i=t.drawingBufferHeight;G.bind(),m.SHADING&&G.uniforms.texelSize&&t.uniform2f(G.uniforms.texelSize,1/r,1/i),G.uniforms.uTexture&&t.uniform1i(G.uniforms.uTexture,D.read.attach(0)),_(e,!1)}function Qe(e){const r=e.deltaX*m.SPLAT_FORCE,i=e.deltaY*m.SPLAT_FORCE;Ee(e.texcoordX,e.texcoordY,r,i,e.color)}function Ze(e){const r=oe();r.r*=10,r.g*=10,r.b*=10;const i=10*(Math.random()-.5),o=30*(Math.random()-.5);Ee(e.texcoordX,e.texcoordY,i,o,r)}function Ee(e,r,i,o,n){T.bind(),T.uniforms.uTarget&&t.uniform1i(T.uniforms.uTarget,l.read.attach(0)),T.uniforms.aspectRatio&&t.uniform1f(T.uniforms.aspectRatio,d.width/d.height),T.uniforms.point&&t.uniform2f(T.uniforms.point,e,r),T.uniforms.color&&t.uniform3f(T.uniforms.color,i,o,0),T.uniforms.radius&&t.uniform1f(T.uniforms.radius,et(m.SPLAT_RADIUS/100)),_(l.write),l.swap(),T.uniforms.uTarget&&t.uniform1i(T.uniforms.uTarget,D.read.attach(0)),T.uniforms.color&&t.uniform3f(T.uniforms.color,n.r,n.g,n.b),_(D.write),D.swap()}function et(e){const r=d.width/d.height;return r>1&&(e*=r),e}function fe(e,r,i,o){e.id=r,e.down=!0,e.moved=!1,e.texcoordX=i/d.width,e.texcoordY=1-o/d.height,e.prevTexcoordX=e.texcoordX,e.prevTexcoordY=e.texcoordY,e.deltaX=0,e.deltaY=0,e.color=oe()}function de(e,r,i,o){e.prevTexcoordX=e.texcoordX,e.prevTexcoordY=e.texcoordY,e.texcoordX=r/d.width,e.texcoordY=1-i/d.height,e.deltaX=rt(e.texcoordX-e.prevTexcoordX),e.deltaY=it(e.texcoordY-e.prevTexcoordY),e.moved=Math.abs(e.deltaX)>0||Math.abs(e.deltaY)>0,e.color=o}function tt(e){e.down=!1}function rt(e){const r=d.width/d.height;return r<1&&(e*=r),e}function it(e){const r=d.width/d.height;return r>1&&(e/=r),e}function oe(){return W[Math.floor(Math.random()*W.length)]}function ot(e,r,i){const o=i-r;return(e-r)%o+r}window.addEventListener("mousedown",e=>{const r=S[0],i=y(e.clientX),o=y(e.clientY);fe(r,-1,i,o),Ze(r)},{signal:s.signal});function ye(e){const r=S[0],i=y(e.clientX),o=y(e.clientY),n=oe();ie(),de(r,i,o,n),document.body.removeEventListener("mousemove",ye)}document.body.addEventListener("mousemove",ye,{signal:s.signal}),window.addEventListener("mousemove",e=>{const r=S[0],i=y(e.clientX),o=y(e.clientY),n=r.color;de(r,i,o,n)},{signal:s.signal});function Se(e){const r=e.targetTouches,i=S[0];for(let o=0;o<r.length;o++){const n=y(r[o].clientX),c=y(r[o].clientY);ie(),fe(i,r[o].identifier,n,c)}document.body.removeEventListener("touchstart",Se)}document.body.addEventListener("touchstart",Se,{signal:s.signal}),window.addEventListener("touchstart",e=>{const r=e.targetTouches,i=S[0];for(let o=0;o<r.length;o++){const n=y(r[o].clientX),c=y(r[o].clientY);fe(i,r[o].identifier,n,c)}},{passive:!0,signal:s.signal}),window.addEventListener("touchmove",e=>{const r=e.targetTouches,i=S[0];for(let o=0;o<r.length;o++){const n=y(r[o].clientX),c=y(r[o].clientY);de(i,n,c,i.color)}},{passive:!0,signal:s.signal}),window.addEventListener("touchend",e=>{const r=e.changedTouches,i=S[0];for(let o=0;o<r.length;o++)tt(i)},{signal:s.signal}),ne(()=>u.simResolution,e=>{m.SIM_RESOLUTION=e,te()}),ne(()=>u.dyeResolution,e=>{m.DYE_RESOLUTION=e,te()}),ne(()=>u.shading,e=>{m.SHADING=e,ge()}),ie()}),(s,E)=>(C(),k("div",{class:ve(["fluid-cursor-layer",u.class]),style:{position:"fixed",inset:"0","z-index":"1",width:"100%",height:"100%","pointer-events":"none"}},[U("canvas",{"aria-hidden":"true",ref_key:"canvasRef",ref:p,style:{display:"block",width:"100%",height:"100%"}},null,512)],2))}}),Rt={class:"welcome-page"},Tt={class:"welcome-content","aria-labelledby":"welcome-title"},Et={class:"welcome-badge"},yt={class:"landing-actions"},St=ae({__name:"LandingView",setup(Y){const u=ft(),h=window.matchMedia("(prefers-reduced-motion: no-preference)").matches;function p(L){const s=lt(u.query.redirect);return{name:L,query:s?{redirect:s}:{}}}return(L,s)=>(C(),k("main",Rt,[O(h)?(C(),_e(vt,{key:0,class:"particles-background-layer",quantity:92,staticity:18,ease:10})):we("",!0),O(h)?(C(),_e(gt,{key:1,class:"fluid-cursor-layer","dye-resolution":768,"splat-force":5200,"splat-radius":.16,"color-update-speed":7})):we("",!0),s[6]||(s[6]=U("div",{class:"welcome-glow welcome-glow-one","aria-hidden":"true"},null,-1)),s[7]||(s[7]=U("div",{class:"welcome-glow welcome-glow-two","aria-hidden":"true"},null,-1)),U("section",Tt,[U("div",Et,[H(O(dt),{size:16}),s[0]||(s[0]=me(" 简立得 简历生成AI助手 ",-1))]),s[3]||(s[3]=U("p",{class:"welcome-eyebrow"},"RESUME, MADE PERSONAL",-1)),H(xt,{id:"welcome-title",class:"welcome-title",text:"你的专属简历，即刻拥有"}),s[4]||(s[4]=U("p",{class:"welcome-subtitle"},"Your exclusive resume, instantly yours",-1)),U("div",yt,[H(O(Fe),{class:"welcome-button welcome-button-primary",to:p("login")},{default:Ae(()=>[s[1]||(s[1]=me("登录 ",-1)),H(O(be),{size:18})]),_:1},8,["to"]),H(O(Fe),{class:"welcome-button welcome-button-secondary",to:p("register")},{default:Ae(()=>[s[2]||(s[2]=me("注册 ",-1)),H(O(be),{size:18})]),_:1},8,["to"])]),s[5]||(s[5]=U("p",{class:"welcome-footnote"},"把你的经历，写成下一段可能",-1))])]))}}),_t=he(St,[["__scopeId","data-v-0df57016"]]);export{_t as default};
