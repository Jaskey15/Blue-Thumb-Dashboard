# Fish Data Validation and Duplicate Handling

## Overview
The fish data validation system distinguishes between true replicate samples (separate collection events) and duplicate data entries using Blue Thumb field work records. This process ensures proper date assignment for replicate collections while averaging genuine duplicate entries.

## The Replicate vs Duplicate Problem

### Challenge
When multiple fish samples exist for the same site and year, it's unclear whether they represent:
- **True Replicates**: Separate collection events conducted on different dates
- **Data Duplicates**: Multiple entries of the same collection event

### Solution Approach
Use Blue Thumb field work records (`BT_fish_collection_dates.csv`) to validate and distinguish between these scenarios based on documented field work activities.

---

## BT Field Work Validation Process

### Data Source
- **File**: `BT_fish_collection_dates.csv`
- **Contains**: Official Blue Thumb field work collection dates and activities
- **Key Fields**: 
  - `Name`: Site name
  - `Date`: Collection date
  - `M/F/H`: Collection type (includes "REP" for replicate collections)

### Site Matching Logic
**Two-tier matching approach:**

1. **Exact Match**: Direct site name match after cleaning
2. **Fuzzy Match**: Similarity-based matching (90% threshold) for slight name variations

```python
def find_bt_site_match(db_site_name, bt_sites, threshold=0.9):
    # Try exact match first
    if db_site_name in bt_sites:
        return db_site_name
    
    # Fall back to fuzzy matching for variants
    best_match = difflib.SequenceMatcher(None, db_site_name.lower(), bt_site.lower()).ratio()
```

### Year Buffer Matching
**±1 Year Buffer**: Accounts for potential year misalignment between database records and BT field work documentation.

**Search Strategy:**
1. Check target year for REP collections
2. Check year-1 for REP collections  
3. Check year+1 for REP collections
4. Requires both original and REP collection records for validation

---

## Replicate Identification and Processing

### Replicate Detection Criteria
A duplicate group is classified as **replicates** when ALL conditions are met:

1. **BT Site Match**: Site name matches BT field work records (exact or fuzzy)
2. **REP Collection Found**: BT records show a "REP" collection type
3. **Original Collection Found**: BT records show corresponding original (non-REP) collection
4. **Date Availability**: Both original and REP dates are available
5. **Year Match**: Within ±1 year buffer of database records

### Date Assignment Process

**For confirmed replicates:**
1. **Sort BT Dates**: Order original and REP collection dates chronologically
2. **Sort Fish Samples**: Order database samples consistently (by sample_id)
3. **Assign Dates**:
   - First sample → Earlier BT date (original collection)
   - Second sample → Later BT date (REP collection)
   - Additional samples → Handle gracefully with sequential numbering

```python
# Assignment example
original_date = rep_data_sorted.iloc[0]['Date_Clean']  # Earlier date
rep_date = rep_data_sorted.iloc[1]['Date_Clean']       # Later date

# Update fish samples
fish_processed.at[idx, 'collection_date'] = original_date  # First sample
fish_processed.at[idx, 'collection_date'] = rep_date       # Second sample
```

### Replicate Processing Impact
- **Date Correction**: Samples get correct collection dates from BT records
- **Year Update**: Sample years updated to match assigned dates
- **Separate Events**: Samples treated as distinct collection events
- **Preserved Data**: All fish community metrics preserved for both samples

---

## Duplicate Averaging Process

### When Averaging Occurs
Groups are averaged when they **fail replicate validation**:
- No BT site match found
- No REP collection in BT records
- Missing original or REP collection dates
- Outside ±1 year buffer range

### Averaging Methodology

#### Core Metric Averaging
- **`comparison_to_reference`**: Average numeric values across samples
- **Base Record**: Use first sample as template for non-numeric fields

#### Individual Score Handling
- **Individual Scores**: Set to NULL (not averaged)
- **Rationale**: Averaging 1,3,5 scale scores creates meaningless intermediate values
- **Preserved**: Overall comparison_to_reference score which is the key metric

```python
def average_group_samples(group):
    # Average the main comparison score
    comparison_values = group['comparison_to_reference'].dropna().tolist()
    if comparison_values:
        avg_comparison = sum(comparison_values) / len(comparison_values)
    
    # Nullify individual metric scores (1,3,5 scale not meaningful when averaged)
    score_columns = [col for col in averaged_row.index if 'score' in str(col).lower()]
    for col in score_columns:
        averaged_row[col] = None
    
    return averaged_row
```

---

## Complete Processing Workflow

### Input Processing
1. **Load BT Data**: Read and clean BT field work records
2. **Identify Duplicate Groups**: Find all site+year combinations with multiple samples
3. **Site Matching**: Match database sites to BT site records

### Group Classification Loop
For each duplicate group:

1. **BT Validation Check**:
   - Find matching BT site name
   - Search for REP collections (±1 year buffer)
   - Verify original collection exists

2. **Process Based on Classification**:
   - **Replicates Found**: Assign BT dates to samples
   - **No Replicates**: Average samples into single record

3. **Update Database Records**:
   - Replicates: Update dates and years
   - Averages: Remove originals, add averaged record

### Output Generation
- **Processed DataFrame**: Updated fish data with corrected dates or averaged records
- **Processing Log**: Summary of replicate groups vs averaged groups
- **Date Assignments**: Detailed log of all date corrections made

---

## Usage Examples

### Basic Usage
```python
from data_processing.bt_fieldwork_validator import categorize_and_process_duplicates, load_bt_field_work_dates

# Load BT field work data
bt_df = load_bt_field_work_dates()

# Process fish duplicates
processed_fish_df = categorize_and_process_duplicates(fish_df, bt_df)
```

### Complete Integration
```python
# In fish processing pipeline
def process_fish_data():
    # Load fish data
    fish_df = load_fish_data()
    
    # Load BT validation data
    bt_df = load_bt_field_work_dates()
    
    # Handle duplicates with BT validation
    if not bt_df.empty:
        fish_df = categorize_and_process_duplicates(fish_df, bt_df)
    else:
        logger.warning("No BT data available - all duplicates will be averaged")
    
    return fish_df
```

---

## Decision Logic Summary

### Replicate vs Duplicate Decision Tree

```
Multiple samples for same site+year?
├─ YES: Check BT field work records
│   ├─ BT site match found?
│   │   ├─ YES: REP collection in BT data (±1 year)?
│   │   │   ├─ YES: Original collection also in BT data?
│   │   │   │   ├─ YES: → REPLICATES (assign BT dates)
│   │   │   │   └─ NO: → DUPLICATES (average)
│   │   │   └─ NO: → DUPLICATES (average)
│   │   └─ NO: → DUPLICATES (average)
│   └─ BT data unavailable: → DUPLICATES (average)
└─ NO: → Single sample (no processing needed)
```

### Key Decision Points

1. **BT Data Availability**: Without BT records, all duplicates are averaged
2. **Site Name Matching**: Fuzzy matching accommodates slight name variations
3. **Year Buffer**: ±1 year accounts for documentation timing differences
4. **REP Collection Requirement**: Must have both original AND REP documented
5. **Date Assignment**: Chronological order ensures consistent date assignment

---

## Impact on Fish Community Analysis

### Before Validation:
- Unclear whether multiple samples represent replicates or data errors
- Potential for incorrect temporal analysis
- Inconsistent treatment of duplicate data
- Possible bias from averaged replicate samples

### After Validation:
- True replicates properly separated with correct collection dates
- Duplicate entries cleaned through averaging
- Consistent temporal analysis with accurate date assignments
- Preserved biological replicate information for statistical analysis

### Benefits for Analysis:

1. **Temporal Accuracy**: Replicate samples get correct collection dates
2. **Statistical Validity**: True replicates preserved for proper analysis
3. **Data Quality**: Duplicate entries resolved consistently
4. **Audit Trail**: Clear documentation of processing decisions
5. **Flexibility**: ±1 year buffer accommodates real-world data variations

### Quality Assurance:

- **BT Validation**: External field work records provide authoritative source
- **Conservative Approach**: Default to averaging when uncertain
- **Detailed Logging**: Track all processing decisions for review
- **Fuzzy Matching**: Accommodate minor site name variations
- **Graceful Degradation**: Handle missing BT data appropriately

---

## Processing Statistics Example

### Typical Processing Summary:
```
Fish duplicate processing: 12 replicate groups, 8 groups averaged, 24 date assignments
```

**Interpretation:**
- **12 replicate groups**: Found BT validation for 12 site+year combinations
- **8 groups averaged**: 8 combinations treated as duplicates and averaged
- **24 date assignments**: 24 individual samples got corrected dates from BT records

### Date Assignment Tracking:
```python
date_assignments.append({
    'site_name': site_name,
    'original_year': year,
    'bt_year_used': year_used,
    'sample_id': sample['sample_id'],
    'assignment_type': assignment_type,  # "Original" or "REP"
    'assigned_date': assigned_date,
    'year_buffer_used': year_used != year
})
```

This detailed tracking enables full audit trails and quality assurance review of the validation process. 