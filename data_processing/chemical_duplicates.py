"""
chemical_duplicates.py - Chemical Data Duplicate Detection and Consolidation
This module handles all duplicate-related operations for chemical data

Key Functions:
- identify_replicate_samples(): Find replicate samples in database
- consolidate_replicate_samples(): Merge replicates using "worst case" values

Workflow:
1. Data insertion now allows duplicate site+date combinations (multiple collection events)
2. Use identify_replicate_samples() to find groups with multiple events for same site+date
3. Use consolidate_replicate_samples() to merge replicates using "worst case" logic:
   - pH: Value furthest from neutral (7.0)
   - DO: Lowest value (worst oxygen saturation)
   - All others: Highest value (worst case for nutrients/pollutants)

Usage:
- Import functions for use in data processing pipeline
"""

import pandas as pd
import numpy as np
from data_processing import setup_logging

# Set up logging
logger = setup_logging("chemical_duplicates", category="processing")

def identify_replicate_samples():
    """
    Identify replicate samples in the database (same site + date combinations).
    
    Returns:
        list: List of dictionaries with replicate group information
    """
    from database.database import get_connection, close_connection
    
    try:
        conn = get_connection()
        
        # Find site-date combinations with multiple collection events
        replicate_query = """
        SELECT s.site_name, c.collection_date, 
               COUNT(*) as event_count,
               GROUP_CONCAT(c.event_id) as event_ids
        FROM chemical_collection_events c
        JOIN sites s ON c.site_id = s.site_id
        GROUP BY s.site_name, c.collection_date
        HAVING COUNT(*) > 1
        ORDER BY s.site_name, c.collection_date
        """
        
        replicate_df = pd.read_sql_query(replicate_query, conn)
        close_connection(conn)
        
        if replicate_df.empty:
            return []
        
        # Convert to list of dictionaries for easier processing
        replicate_groups = []
        for _, row in replicate_df.iterrows():
            event_ids = [int(id.strip()) for id in row['event_ids'].split(',')]
            replicate_groups.append({
                'site_name': row['site_name'],
                'collection_date': row['collection_date'],
                'event_count': row['event_count'],
                'event_ids': event_ids,
                'keep_event_id': min(event_ids)  # Keep the one with lowest ID
            })
        
        return replicate_groups
        
    except Exception as e:
        logger.error(f"Error identifying replicate samples: {e}")
        return []

def get_worst_case_value(values, parameter_name):
    """
    Get the "worst case" value for a parameter from a list of values.
    
    Args:
        values: List of parameter values (may contain None/NaN)
        parameter_name: Name of parameter to determine worst case logic
        
    Returns:
        float: Worst case value, or None if all values are null
    """
    # Filter out null values
    valid_values = [v for v in values if pd.notna(v) and v is not None]
    
    if not valid_values:
        return None
    
    # Apply parameter-specific logic
    if parameter_name == 'pH':
        # Furthest from neutral (pH 7)
        return max(valid_values, key=lambda x: abs(x - 7.0))
    elif parameter_name == 'do_percent':
        # Lowest dissolved oxygen is worst
        return min(valid_values)
    else:
        # For all other parameters (nutrients, chloride), highest is worst
        return max(valid_values)

def consolidate_replicate_samples():
    """
    Consolidate replicate samples by merging them into single collection events.
    
    Returns:
        dict: Summary of consolidation results
    """
    from database.database import get_connection, close_connection
    from data_processing.chemical_utils import PARAMETER_MAP, determine_status, get_reference_values
    
    try:
        # Step 1: Identify replicate groups
        replicate_groups = identify_replicate_samples()
        
        if not replicate_groups:
            return {
                'groups_processed': 0,
                'events_removed': 0,
                'measurements_updated': 0
            }
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get reference values for status determination
        reference_values = get_reference_values()
        
        # Track statistics
        stats = {
            'groups_processed': 0,
            'events_removed': 0,
            'measurements_updated': 0
        }
        
        # Process each replicate group
        for group in replicate_groups:
            site_name = group['site_name']
            collection_date = group['collection_date']
            event_ids = group['event_ids']
            keep_event_id = group['keep_event_id']
            remove_event_ids = [eid for eid in event_ids if eid != keep_event_id]
            
            # Get all measurements for this replicate group
            measurements_query = """
            SELECT cm.event_id, cm.parameter_id, cm.value, cp.parameter_code
            FROM chemical_measurements cm
            JOIN chemical_parameters cp ON cm.parameter_id = cp.parameter_id
            WHERE cm.event_id IN ({})
            """.format(','.join('?' * len(event_ids)))
            
            measurements_df = pd.read_sql_query(measurements_query, conn, params=event_ids)
            
            if measurements_df.empty:
                continue
            
            # Group by parameter and find worst case values
            consolidated_measurements = {}
            for parameter_id in measurements_df['parameter_id'].unique():
                param_data = measurements_df[measurements_df['parameter_id'] == parameter_id]
                parameter_code = param_data['parameter_code'].iloc[0]
                values = param_data['value'].tolist()
                
                worst_value = get_worst_case_value(values, parameter_code)
                
                if worst_value is not None:
                    # Determine status for the consolidated value
                    status = determine_status(parameter_code, worst_value, reference_values)
                    consolidated_measurements[parameter_id] = {
                        'value': worst_value,
                        'status': status,
                        'parameter_code': parameter_code,
                        'original_values': values
                    }
            
            # Update measurements in the kept event
            for parameter_id, measurement_data in consolidated_measurements.items():
                # Check if measurement exists in kept event
                existing_query = """
                SELECT 1 FROM chemical_measurements 
                WHERE event_id = ? AND parameter_id = ?
                """
                existing = cursor.execute(existing_query, (keep_event_id, parameter_id)).fetchone()
                
                if existing:
                    # Update existing measurement
                    cursor.execute("""
                    UPDATE chemical_measurements 
                    SET value = ?, status = ?
                    WHERE event_id = ? AND parameter_id = ?
                    """, (measurement_data['value'], measurement_data['status'], 
                          keep_event_id, parameter_id))
                else:
                    # Insert new measurement
                    cursor.execute("""
                    INSERT INTO chemical_measurements (event_id, parameter_id, value, status)
                    VALUES (?, ?, ?, ?)
                    """, (keep_event_id, parameter_id, measurement_data['value'], 
                          measurement_data['status']))
                
                stats['measurements_updated'] += 1
            
            # Delete the other events (cascade will delete their measurements)
            for remove_event_id in remove_event_ids:
                cursor.execute("DELETE FROM chemical_collection_events WHERE event_id = ?", 
                             (remove_event_id,))
                stats['events_removed'] += 1
            
            stats['groups_processed'] += 1
        
        conn.commit()
        close_connection(conn)
        
        # Log concise summary
        logger.info(f"Chemical duplicate consolidation: {stats['groups_processed']} groups, {stats['events_removed']} events removed, {stats['measurements_updated']} measurements updated")
        
        return stats
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            close_connection(conn)
        logger.error(f"Error consolidating replicate samples: {e}")
        raise Exception(f"Failed to consolidate replicate samples: {e}")

 