# Custom Process Creation Feature

## Overview

Users can now create custom processes on-the-fly by entering process names separated by commas.

## How to Use

### Step 1: Select Custom Mode

1. Open the scenario dropdown menu
2. Select **"✨ Custom Processes"** option

### Step 2: Enter Process Names

A text input field will appear where you can enter process names:

- **Format**: `P1,P2,P3,P4,P5` or `P1, P2, P3, P4, P5`
- **Case-insensitive**: `p1,p2,p3` will be converted to `P1,P2,P3`
- **Spaces are optional**: Both `P1,P2` and `P1, P2` are accepted
- **Any number of processes**: Add as many as you need

### Step 3: Create Processes

- Click the **"✨ Create Processes"** button, OR
- Press **Enter** key while typing

## Features

✅ **Flexible Input**: Accepts comma-separated names  
✅ **Validation**:

- Prevents empty input
- Removes duplicates (checks for duplicate names)
- Auto-trims whitespace
- Case normalization

✅ **Automatic Scenario**:

- Creates pipe connections between consecutive processes
- Sets up communication steps
- Generates a runnable simulation

✅ **Error Handling**:

- Shows error messages in the log
- Validates duplicate names
- Requires at least one process

## Example Usage

### Example 1: Simple 3-process pipeline

```
Input: P1,P2,P3
Result: Creates P1 → P2 → P3 communication chain
```

### Example 2: 5 processes with spacing

```
Input: Worker1, Worker2, Worker3, Worker4, Worker5
Result: Processes connected in sequence with auto-converted names
```

### Example 3: Complex naming

```
Input: Server, Client, Logger, Cache, Database
Result: Five-process pipeline with custom names
```

## Implementation Details

### Files Modified

1. **index.html**: Added custom process input section
2. **css/styles.css**: Styled the custom input field and button
3. **js/app.js**: Added `createCustomProcesses()` method

### Auto-Generated Scenario

When custom processes are created, the system automatically:

1. Initializes all processes (first as running, others as ready)
2. Creates pipe connections between consecutive processes
3. Generates communication steps for the pipeline
4. Sets up message flow visualization
5. Enables play/pause/step controls

### Input Validation

- Trims whitespace from each process name
- Converts to uppercase for consistency
- Checks for duplicate names
- Requires non-empty input
- Filters out empty entries

## Technical Implementation

```javascript
// Example: How createCustomProcesses() works internally
const input = 'P1,P2,P3,P4,P5';
// Parsed into: ["P1", "P2", "P3", "P4", "P5"]
// Creates 5 processes
// Connects: P1→P2, P2→P3, P3→P4, P4→P5
// Generates communication steps for simulation
```

## Keyboard Shortcuts

- **Enter key**: Trigger process creation while typing in the input field
- **Tab**: Navigate to the Create button

## Accessibility

- Full ARIA labels for screen readers
- Keyboard navigable
- Clear placeholder text
- Live region updates for status messages
