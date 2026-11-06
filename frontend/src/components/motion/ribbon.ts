/**
 * Ribbon field formula adapted from ThreeUI, Copyright (c) 2026 Meng To.
 * MIT license: /licenses/ThreeUI-MIT.txt. Palette, renderer and lifecycle are local.
 */
export function mountRibbon(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  isPaused: () => boolean = () => false,
) {
  const gl = canvas.getContext('webgl', {
    alpha: false,
    antialias: false,
    depth: false,
    powerPreference: 'low-power',
  });
  if (!gl) return () => {};
  const shaders: WebGLShader[] = [];
  let program: WebGLProgram | null = null;
  let buffer: WebGLBuffer | null = null;
  let frame = 0,
    disposed = false,
    visible = true,
    last = 0,
    clock = 0;

  let pointerX = 0.5;
  const vertex = 'attribute vec2 position; void main(){gl_Position=vec4(position,0.,1.);}';
  const fragment = `
    precision mediump float;
    uniform vec2 resolution;
    uniform float time;
    uniform float pointer;
    uniform vec3 paper;
    uniform vec3 ice;
    uniform vec3 mint;
    float ribbon(vec2 uv,float offset,float width,float phase) {
      float y=.55+.20*sin(uv.x*2.15+phase)+.045*sin(uv.x*7.-phase*.7);
      float d=abs(uv.y-y-offset);
      return exp(-(d*d)/width);
    }
    void main(){
      vec2 uv=gl_FragCoord.xy/resolution;
      float t=time*.65;
      float drift=(pointer-.5)*.18;
      float a=ribbon(vec2(uv.x+drift,uv.y),.03,.0065,t+.9);
      float b=ribbon(vec2(uv.x-drift*.7,uv.y),-.23,.0085,t+3.25);
      float right=.55+.45*smoothstep(.0,.9,uv.x);
      vec3 color=mix(paper,ice,a*right*.80);
      color=mix(color,mint,b*right*.72);
      gl_FragColor=vec4(color,1.);
    }
  `;
  function compile(type: number, source: string) {
    const shader = gl!.createShader(type);
    if (!shader) throw new Error('shader allocation');
    shaders.push(shader);
    gl!.shaderSource(shader, source);
    gl!.compileShader(shader);
    if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) throw new Error('shader compile');
    return shader;
  }
  try {
    program = gl.createProgram();
    if (!program) throw new Error('program allocation');
    gl.attachShader(program, compile(gl.VERTEX_SHADER, vertex));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragment));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('program link');
    gl.useProgram(program);
    buffer = gl.createBuffer();
    if (!buffer) throw new Error('buffer allocation');
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW,
    );
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const styles = getComputedStyle(document.documentElement);
    for (const [uniform, token] of [
      ['paper', '--color-ribbon-paper'],
      ['ice', '--color-ribbon-ice'],
      ['mint', '--color-ribbon-mint'],
    ]) {
      const hex = styles.getPropertyValue(token!).trim().replace('#', '');
      const rgb = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
      gl.uniform3f(gl.getUniformLocation(program, uniform!), rgb[0]!, rgb[1]!, rgb[2]!);
    }
  } catch {
    shaders.forEach((s) => gl.deleteShader(s));
    gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
    return () => {};
  }
  const resolution = gl.getUniformLocation(program, 'resolution');
  const time = gl.getUniformLocation(program, 'time');
  const pointer = gl.getUniformLocation(program, 'pointer');
  function draw(now: number) {
    if (disposed || !visible || document.hidden || isPaused()) {
      frame = 0;
      return;
    }
    if (now - last >= 33) {
      clock += Math.min((now - last) / 1000, 0.05);
      last = now;
      gl!.uniform2f(resolution, canvas.width, canvas.height);
      gl!.uniform1f(time, clock);
      gl!.uniform1f(pointer, pointerX);
      gl!.drawArrays(gl!.TRIANGLES, 0, 6);
      canvas.classList.add('ribbon-ready');
    }
    frame = requestAnimationFrame(draw);
  }
  function wake() {
    if (disposed || !visible || document.hidden) return;

    if (!frame) frame = requestAnimationFrame(draw);
  }
  const resize = new ResizeObserver(() => {
    const rect = host.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    gl!.viewport(0, 0, canvas.width, canvas.height);
    wake();
  });
  resize.observe(host);
  const intersection = new IntersectionObserver(([entry]) => {
    visible = !!entry?.isIntersecting;
    if (visible) wake();
    else {
      cancelAnimationFrame(frame);
      frame = 0;
    }
  });
  intersection.observe(host);
  function move(event: PointerEvent) {
    const rect = host.getBoundingClientRect();
    pointerX = (event.clientX - rect.left) / Math.max(rect.width, 1);
    wake();
  }
  function visibility() {
    if (document.hidden) {
      cancelAnimationFrame(frame);
      frame = 0;
    } else wake();
  }
  function lost(event: Event) {
    event.preventDefault();
    cancelAnimationFrame(frame);
    frame = 0;
    canvas.classList.remove('ribbon-ready');
    cleanup();
  }
  host.addEventListener('pointermove', move, { passive: true });
  host.addEventListener('ribbon-play', wake);
  canvas.addEventListener('webglcontextlost', lost);
  document.addEventListener('visibilitychange', visibility);
  function cleanup() {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    resize.disconnect();
    intersection.disconnect();
    host.removeEventListener('pointermove', move);
    host.removeEventListener('ribbon-play', wake);
    canvas.removeEventListener('webglcontextlost', lost);
    document.removeEventListener('visibilitychange', visibility);
    shaders.forEach((s) => gl!.deleteShader(s));
    gl!.deleteBuffer(buffer);
    gl!.deleteProgram(program);
  }
  return cleanup;
}
