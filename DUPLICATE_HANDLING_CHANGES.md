# Chemical Data Duplicate Handling Changes

## Overview
Modified the chemical data processing system to allow duplicate site+date combinations during insertion, then handle consolidation using the existing `chemical_duplicates.py` module.

## Changes Made

### 1. Database Schema
**No changes required** - The `chemical_collection_events` table already allows multiple events for the same site+date combination (no unique constraints exist).

### 2. Chemical Utils (`data_processing/chemical_utils.py`)

#### Modified Functions:
- **`get_existing_data(conn)`**: 
  - Removed tracking of existing collection events
  - Now only tracks existing measurements and site lookups
  - Returns: `(existing_measurements, site_lookup)` instead of 4-tuple

- **`insert_collection_event()`**:
  - Simplified to always create new collection events
  - Removed duplicate checking logic
  - Always increments event counter in statistics

- **`insert_chemical_data()`**:
  - Renamed parameter from `check_duplicates` to `allow_duplicates` (default True)
  - Updated docstring to clarify new behavior
  - Now always creates new events for each row of data

### 3. Updated Processing Files

#### `data_processing/chemical_processing.py`:
- Updated call to `insert_chemical_data()` to remove old parameter
- Added comment clarifying that duplicates are now allowed by default

#### `data_processing/updated_chemical_processing.py`:
- Updated call to `insert_chemical_data()` to remove old parameter

### 4. Enhanced Documentation

#### `chemical_duplicates.py`:
- Updated module docstring to explain the new workflow
- Clarified the "worst case" consolidation logic:
  - **pH**: Value furthest from neutral (7.0)
  - **DO**: Lowest value (worst oxygen saturation)  
  - **All others**: Highest value (worst case for nutrients/pollutants)

### 5. Test Script

#### `test_duplicate_workflow.py` (NEW):
- Demonstrates the complete workflow:
  1. Insert duplicate site+date combinations
  2. Identify replicate samples
  3. Run consolidation in dry-run mode
  4. Execute actual consolidation
  5. Verify cleanup completed

## New Workflow

### Before (Previous Behavior):
1. Data insertion prevented duplicates by checking existing site+date combinations
2. Only one collection event per site+date was allowed
3. Duplicate detection was manual/external

### After (New Behavior):
1. **Data Insertion**: Multiple collection events can be created for same site+date
2. **Duplicate Detection**: Use `identify_replicate_samples()` to find replicate groups
3. **Consolidation**: Use `consolidate_replicate_samples()` with "worst case" logic
4. **Result**: Clean database with single collection event per site+date using consolidated values

## Usage Examples

### Insert Data with Duplicates:
```python
from data_processing.chemical_utils import insert_chemical_data

# This will now create separate collection events for each row,
# even if they have the same site+date
stats = insert_chemical_data(dataframe, data_source="my_data_source")
```

### Consolidate Replicates:
```python
from data_processing.chemical_duplicates import consolidate_replicate_samples

# Run in dry-run mode first to see what would happen
dry_stats = consolidate_replicate_samples(dry_run=True)

# Execute the actual consolidation
live_stats = consolidate_replicate_samples(dry_run=False)
```

### Complete Test Workflow:
```bash
python test_duplicate_workflow.py
```

## Benefits

1. **Flexibility**: Can now handle datasets with genuine replicate samples
2. **Data Integrity**: "Worst case" logic ensures conservative water quality assessments
3. **Transparency**: Clear logging shows how values are consolidated
4. **Safety**: Dry-run mode allows preview before making changes
5. **Backwards Compatibility**: Existing data processing continues to work

## Impact on Existing Data

- **No impact**: Existing single collection events remain unchanged
- **Future processing**: New data can contain replicates that get consolidated
- **Manual cleanup**: Run `consolidate_replicate_samples()` on existing database if needed 