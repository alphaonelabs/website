/**
 * robot_blocks.js — custom Blockly block definitions for robot commands.
 * Plain JS, no ES modules, no build step required.
 * Runs at load time after Blockly is on the page.
 */

/* ── robot_move_forward ──────────────────────────────────────────────── */
Blockly.Blocks['robot_move_forward'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('Move Forward')
        .appendField(new Blockly.FieldNumber(10, 1, 100), 'STEPS')
        .appendField('steps');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(210);
    this.setTooltip('Move the robot forward by the given number of steps');
  }
};
Blockly.JavaScript['robot_move_forward'] = function (block) {
  const steps = block.getFieldValue('STEPS');
  return 'RobotAPI.moveForward(' + steps + ');\n';
};

/* ── robot_move_backward ─────────────────────────────────────────────── */
Blockly.Blocks['robot_move_backward'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('Move Backward')
        .appendField(new Blockly.FieldNumber(10, 1, 100), 'STEPS')
        .appendField('steps');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(210);
    this.setTooltip('Move the robot backward by the given number of steps');
  }
};
Blockly.JavaScript['robot_move_backward'] = function (block) {
  const steps = block.getFieldValue('STEPS');
  return 'RobotAPI.moveBackward(' + steps + ');\n';
};

/* ── robot_turn_left ─────────────────────────────────────────────────── */
Blockly.Blocks['robot_turn_left'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('Turn Left')
        .appendField(new Blockly.FieldNumber(90, 0, 360), 'DEGREES')
        .appendField('degrees');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(120);
    this.setTooltip('Turn the robot left by the given number of degrees');
  }
};
Blockly.JavaScript['robot_turn_left'] = function (block) {
  const degrees = block.getFieldValue('DEGREES');
  return 'RobotAPI.turnLeft(' + degrees + ');\n';
};

/* ── robot_turn_right ────────────────────────────────────────────────── */
Blockly.Blocks['robot_turn_right'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('Turn Right')
        .appendField(new Blockly.FieldNumber(90, 0, 360), 'DEGREES')
        .appendField('degrees');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(120);
    this.setTooltip('Turn the robot right by the given number of degrees');
  }
};
Blockly.JavaScript['robot_turn_right'] = function (block) {
  const degrees = block.getFieldValue('DEGREES');
  return 'RobotAPI.turnRight(' + degrees + ');\n';
};

/* ── robot_wait ──────────────────────────────────────────────────────── */
Blockly.Blocks['robot_wait'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('Wait')
        .appendField(new Blockly.FieldNumber(500, 100, 5000), 'MS')
        .appendField('ms');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(30);
    this.setTooltip('Pause the robot for the given number of milliseconds');
  }
};
Blockly.JavaScript['robot_wait'] = function (block) {
  const ms = block.getFieldValue('MS');
  return 'await RobotAPI.wait(' + ms + ');\n';
};

/* ── robot_scan ──────────────────────────────────────────────────────── */
Blockly.Blocks['robot_scan'] = {
  init: function () {
    this.appendDummyInput()
        .appendField('LiDAR Scan');
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(260);
    this.setTooltip('Perform a LiDAR scan and log the nearest obstacle distance');
  }
};
Blockly.JavaScript['robot_scan'] = function (block) {
  return 'RobotAPI.scan();\n';
};
