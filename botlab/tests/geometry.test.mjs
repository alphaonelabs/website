import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beamIntersectsBlock,
  getColorName,
  pointToSegmentDist,
  segmentIntersectsRect,
  segmentsIntersect,
} from '../js/geometry.js';

test('segmentsIntersect detects crossing segments', () => {
  assert.equal(segmentsIntersect(0, 0, 10, 10, 0, 10, 10, 0), true);
});

test('segmentsIntersect rejects parallel segments', () => {
  assert.equal(segmentsIntersect(0, 0, 10, 0, 0, 2, 10, 2), false);
});

test('segmentsIntersect rejects disjoint segments', () => {
  assert.equal(segmentsIntersect(0, 0, 2, 2, 3, 0, 5, 2), false);
});

test('segmentIntersectsRect detects a beam ending inside a rectangle', () => {
  assert.equal(segmentIntersectsRect(0, 15, 15, 15, 10, 10, 20, 20), true);
});

test('beamIntersectsBlock detects a square hit', () => {
  assert.equal(
    beamIntersectsBlock(0, 20, 40, 20, { x: 10, y: 10, size: 20, shape: 'square' }),
    true,
  );
});

test('beamIntersectsBlock detects a circle hit', () => {
  assert.equal(
    beamIntersectsBlock(0, 20, 40, 20, { x: 10, y: 10, size: 20, shape: 'circle' }),
    true,
  );
});

test('beamIntersectsBlock rejects a circle miss', () => {
  assert.equal(
    beamIntersectsBlock(0, 31, 40, 31, { x: 10, y: 10, size: 20, shape: 'circle' }),
    false,
  );
});

test('beamIntersectsBlock detects a triangle hit', () => {
  assert.equal(
    beamIntersectsBlock(0, 20, 40, 20, { x: 10, y: 10, size: 20, shape: 'triangle' }),
    true,
  );
});

test('beamIntersectsBlock rejects a triangle miss', () => {
  assert.equal(
    beamIntersectsBlock(0, 35, 40, 35, { x: 10, y: 10, size: 20, shape: 'triangle' }),
    false,
  );
});

test('pointToSegmentDist measures distance to a segment', () => {
  assert.equal(pointToSegmentDist(5, 3, 0, 0, 10, 0), 3);
});

test('pointToSegmentDist measures distance to a zero-length segment', () => {
  assert.equal(pointToSegmentDist(3, 4, 0, 0, 0, 0), 5);
});

test('getColorName maps hue 0 to red', () => {
  assert.equal(getColorName('hsl(0, 100%, 50%)'), 'Red');
});

test('getColorName maps hue 360 to red', () => {
  assert.equal(getColorName('hsl(360, 100%, 50%)'), 'Red');
});

test('getColorName returns non-HSL colors unchanged', () => {
  assert.equal(getColorName('rebeccapurple'), 'rebeccapurple');
});
