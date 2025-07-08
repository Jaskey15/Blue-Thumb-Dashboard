"""
Detects and consolidates duplicate chemical data entries using a "worst-case" approach.

This module provides functions to identify and merge replicate chemical samples 
from the database. The consolidation logic selects the "worst-case" value for 
each parameter (e.g., highest for nutrients, lowest for dissolved oxygen) to ensure
the most conservative representation of water quality is retained.
"""

import pandas as pd
import numpy as np
from data_processing import setup_logging

logger = setup_logging("chemical_duplicates", category="processing")

def identify_replicate_samples():
    """Identifies replicate chemical samples from the database."""
    from database.database import get_connection, close_connection
    
    try:
        conn = get_connection()
        
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
        
        replicate_groups = []
        for _, row in replicate_df.iterrows():
            event_ids = [int(id.strip()) for id in row['event_ids'].split(',')]
            replicate_groups.append({
                'site_name': row['site_name'],
                'collection_date': row['collection_date'],
                'event_count': row['event_count'],
                'event_ids': event_ids,
                'keep_event_id': min(event_ids)  # Keep event with the lowest ID for consistency
            })
        
        return replicate_groups
        
    except Exception as e:
        logger.error(f"Error identifying replicate samples: {e}")
        return []

def get_worst_case_value(values, parameter_name):
    """
    Determines the "worst-case" value from a list based on the parameter.
    
    Args:
        values: A list of parameter values, which may contain None or NaN.
        parameter_name: The name of the parameter, used to determine worst-case logic.
        
    Returns:
        The worst-case value, or None if all input values are null.
    """
    valid_values = [v for v in values if pd.notna(v) and v is not None]
    
    if not valid_values:
        return None
    
    if parameter_name == 'pH':
        # For pH, the value furthest from neutral (7.0) is considered the worst case.
        return max(valid_values, key=lambda x: abs(x - 7.0))
    elif parameter_name == 'do_percent':
        # For dissolved oxygen, the lowest percentage is the worst case for aquatic life.
        return min(valid_values)
    else:
        # For nutrients and other pollutants, the highest concentration is the worst case.
        return max(valid_values)

def consolidate_replicate_samples():
    """
    Identifies and consolidates replicate samples using worst-case logic.
    
    Returns:
        A dictionary summarizing the consolidation results.
    """
    from database.database import get_connection, close_connection
    from data_processing.chemical_utils import PARAMETER_MAP, determine_status, get_reference_values
    
    try:
        replicate_groups = identify_replicate_samples()
        
        if not replicate_groups:
            return {
                'groups_processed': 0,
                'events_removed': 0,
                'measurements_updated': 0
            }
        
        conn = get_connection()
        cursor = conn.cursor()
        
        reference_values = get_reference_values()
        
        stats = {
            'groups_processed': 0,
            'events_removed': 0,
            'measurements_updated': 0
        }
        
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
            
            consolidated_measurements = {}
            for parameter_id in measurements_df['parameter_id'].unique():
                param_data = measurements_df[measurements_df['parameter_id'] == parameter_id]
                parameter_code = param_data['parameter_code'].iloc[0]
                values = param_data['value'].tolist()
                
                worst_value = get_worst_case_value(values, parameter_code)
                
                if worst_value is not None:
                    status = determine_status(parameter_code, worst_value, reference_values)
                    consolidated_measurements[parameter_id] = {
                        'value': worst_value,
                        'status': status,
                        'parameter_code': parameter_code,
                        'original_values': values
                    }
            
            for parameter_id, measurement_data in consolidated_measurements.items():
                existing_query = """
                SELECT 1 FROM chemical_measurements 
                WHERE event_id = ? AND parameter_id = ?
                """
                existing = cursor.execute(existing_query, (keep_event_id, parameter_id)).fetchone()
                
                if existing:
                    cursor.execute("""
                    UPDATE chemical_measurements 
                    SET value = ?, status = ?
                    WHERE event_id = ? AND parameter_id = ?
                    """, (measurement_data['value'], measurement_data['status'], 
                          keep_event_id, parameter_id))
                else:
                    cursor.execute("""
                    INSERT INTO chemical_measurements (event_id, parameter_id, value, status)
                    VALUES (?, ?, ?, ?)
                    """, (keep_event_id, parameter_id, measurement_data['value'], 
                          measurement_data['status']))
                
                stats['measurements_updated'] += 1
            
            # Deleting the other events will also delete their measurements due to cascade settings.
            for remove_event_id in remove_event_ids:
                cursor.execute("DELETE FROM chemical_collection_events WHERE event_id = ?", 
                             (remove_event_id,))
                stats['events_removed'] += 1
            
            stats['groups_processed'] += 1
        
        conn.commit()
        close_connection(conn)
        
        logger.info(f"Chemical duplicate consolidation: {stats['groups_processed']} groups, {stats['events_removed']} events removed, {stats['measurements_updated']} measurements updated")
        
        return stats
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            close_connection(conn)
        logger.error(f"Error consolidating replicate samples: {e}")
        raise Exception(f"Failed to consolidate replicate samples: {e}")

 