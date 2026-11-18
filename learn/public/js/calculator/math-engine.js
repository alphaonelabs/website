/**
 * Math Engine: Expression normalization, mathjs parsing, and compilation.
 */

/**
 * Strips leading declarations like "y =", "f(x) =", "g(x) =".
 * @param {string} raw
 * @returns {string}
 */
export function normalizeExpr(raw) {
  let e = (raw || '').trim();
  e = e.replace(/^[yfg]\s*\(?\s*x\s*\)?\s*=\s*/i, '').replace(/^y\s*=\s*/i, '');
  return e;
}

/**
 * Splits comma-separated expressions at depth 0 (ignoring commas inside parentheses/brackets).
 * @param {string} str
 * @returns {string[]}
 */
export function splitTopLevel(str) {
  const parts = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < str.length; i++) {
    const c = str[i];
    if (c === '(' || c === '[') depth++;
    else if (c === ')' || c === ']') depth--;
    else if (c === ',' && depth === 0) {
      parts.push(str.slice(start, i));
      start = i + 1;
    }
  }
  parts.push(str.slice(start));
  return parts;
}

/**
 * Formats mathjs parser errors into user-friendly messages.
 * @param {string} msg
 * @param {string} expr
 * @returns {string}
 */
export function friendlyErr(msg, expr) {
  if (/unexpected token|syntax|Unexpected/i.test(msg)) {
    return `"${expr}" — invalid syntax`;
  }
  if (/undefined symbol|Undefined/i.test(msg)) {
    return `"${expr}" — unknown function or variable`;
  }
  if (/complex/i.test(msg)) {
    return `"${expr}" — result is complex (domain error)`;
  }
  return `"${expr}" — ${msg.split('\n')[0]}`;
}

/**
 * Compiles a single expression string into an evaluatable JavaScript function using mathjs.
 * @param {string} exprStr
 * @returns {((x: number) => number) | null}
 */
export function compileFn(exprStr) {
  const e = normalizeExpr(exprStr);
  if (!e) return null;

  const mathObj = window.math;
  if (!mathObj || typeof mathObj.compile !== 'function') {
    throw new Error('mathjs library is not loaded');
  }

  const compiled = mathObj.compile(e);
  return function evaluateAt(x) {
    const scope = { x, pi: Math.PI, e: Math.E, tau: 2 * Math.PI };
    const result = compiled.evaluate(scope);
    if (typeof result !== 'number') return NaN;
    return result;
  };
}

/**
 * Compiles an equation which may consist of one or multiple expressions (e.g. circle ±sqrt).
 * Sets `eq.fns` and `eq.errors`.
 * @param {Object} eq - Equation object with { raw, fns, errors }
 */
export function compileEquation(eq) {
  eq.fns = [];
  eq.errors = [];

  const exprList = Array.isArray(eq.raw) ? eq.raw : [eq.raw];
  for (const expr of exprList) {
    if (!expr || !expr.trim()) continue;
    try {
      const fn = compileFn(expr);
      if (fn) {
        fn(0); // Test execution to catch any runtime evaluation error early
        eq.fns.push(fn);
      }
    } catch (err) {
      eq.errors.push(friendlyErr(err.message, expr));
    }
  }
}
