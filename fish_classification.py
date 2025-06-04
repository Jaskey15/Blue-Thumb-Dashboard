import pandas as pd
import numpy as np

# Load your processed fish data
df = pd.read_csv('data/processed/processed_fish_data.csv')

# Focus on the two columns we need
analysis_df = df[['comparison_to_reference', 'integrity_class']].copy()

# Remove any remaining invalid values (just in case)
analysis_df = analysis_df[analysis_df['integrity_class'].notna()]
analysis_df = analysis_df[analysis_df['comparison_to_reference'].notna()]

print("=== FISH INTEGRITY CLASS CUTOFF ANALYSIS ===\n")

# 1. Get overview of the data
print("1. DATA OVERVIEW:")
print(f"Total records: {len(analysis_df)}")
print(f"Unique integrity classes: {sorted(analysis_df['integrity_class'].unique())}")
print(f"Score range: {analysis_df['comparison_to_reference'].min():.3f} to {analysis_df['comparison_to_reference'].max():.3f}")
print()

# 2. Count by integrity class
print("2. RECORDS BY INTEGRITY CLASS:")
class_counts = analysis_df['integrity_class'].value_counts().sort_index()
for class_name, count in class_counts.items():
    print(f"  {class_name}: {count} records")
print()

# 3. Find boundaries for each class
print("3. SCORE BOUNDARIES BY CLASS:")
for class_name in sorted(analysis_df['integrity_class'].unique()):
    class_data = analysis_df[analysis_df['integrity_class'] == class_name]['comparison_to_reference']
    min_score = class_data.min()
    max_score = class_data.max()
    print(f"  {class_name}: {min_score:.6f} to {max_score:.6f}")
print()

# 4. Find the exact transition points
print("4. TRANSITION POINT ANALYSIS:")
print("(Where classifications change)")

# Sort by score to see transitions
sorted_df = analysis_df.sort_values('comparison_to_reference')

# Find where classification changes
transitions = []
prev_class = None
for idx, row in sorted_df.iterrows():
    current_class = row['integrity_class']
    current_score = row['comparison_to_reference']
    
    if prev_class is not None and prev_class != current_class:
        transitions.append({
            'from_class': prev_class,
            'to_class': current_class,
            'score': current_score,
            'prev_score': prev_score
        })
    
    prev_class = current_class
    prev_score = current_score

for transition in transitions:
    print(f"  {transition['from_class']} → {transition['to_class']} at score {transition['score']:.6f}")
    print(f"    (Previous score was {transition['prev_score']:.6f})")
print()

# 5. Check for overlaps (inconsistencies)
print("5. CONSISTENCY CHECK:")
print("Looking for score ranges where multiple classes exist...")

overlap_found = False
for class1 in sorted(analysis_df['integrity_class'].unique()):
    for class2 in sorted(analysis_df['integrity_class'].unique()):
        if class1 >= class2:  # Only check each pair once
            continue
            
        class1_data = analysis_df[analysis_df['integrity_class'] == class1]['comparison_to_reference']
        class2_data = analysis_df[analysis_df['integrity_class'] == class2]['comparison_to_reference']
        
        # Check if ranges overlap
        class1_min, class1_max = class1_data.min(), class1_data.max()
        class2_min, class2_max = class2_data.min(), class2_data.max()
        
        if (class1_min <= class2_max and class1_max >= class2_min):
            print(f"  OVERLAP: {class1} ({class1_min:.3f}-{class1_max:.3f}) and {class2} ({class2_min:.3f}-{class2_max:.3f})")
            overlap_found = True

if not overlap_found:
    print("  ✓ No overlaps found - classifications are consistent!")
print()

# 6. Proposed cutoffs based on the data
print("6. PROPOSED CUTOFFS:")
print("Based on the transition analysis above:")

# Get the boundaries in order
class_boundaries = {}
for class_name in sorted(analysis_df['integrity_class'].unique()):
    class_data = analysis_df[analysis_df['integrity_class'] == class_name]['comparison_to_reference']
    class_boundaries[class_name] = (class_data.min(), class_data.max())

# Sort classes by their minimum score
sorted_classes = sorted(class_boundaries.items(), key=lambda x: x[1][0])

for i, (class_name, (min_score, max_score)) in enumerate(sorted_classes):
    if i == 0:
        print(f"  {class_name}: < {max_score:.3f}")
    elif i == len(sorted_classes) - 1:
        print(f"  {class_name}: >= {min_score:.3f}")
    else:
        print(f"  {class_name}: {min_score:.3f} to < {max_score:.3f}")

print("\n=== ANALYSIS COMPLETE ===")