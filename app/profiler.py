import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def profile_excel_file(file_path: str) -> Dict[str, Any]:
    """
    Profiles an Excel file and returns a structured dictionary containing
    detailed metadata, statistics, and a markdown summary of the sheets.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        return {"error": f"Failed to load Excel file: {str(e)}"}
    
    sheets_profile = {}
    relationship_hints = []
    
    # Store columns across sheets to detect foreign/primary keys later
    all_sheet_cols = {}
    
    for sheet_name in xls.sheet_names:
        try:
            # Read sheet (limit rows if massive, but for profiling we load it or chunk it)
            # Power BI models usually profile up to 100k or full sheet if small
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            row_count, col_count = df.shape
            all_sheet_cols[sheet_name] = {
                "cols": list(df.columns),
                "dtypes": {col: str(df[col].dtype) for col in df.columns},
                "unique_counts": {col: df[col].nunique() for col in df.columns},
                "row_count": row_count
            }
            
            columns_data = []
            for col in df.columns:
                series = df[col]
                non_null_count = int(series.count())
                null_count = int(row_count - non_null_count)
                null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0
                unique_val_count = int(series.nunique())
                
                # Inferred Type
                inferred_type = "Text"
                sample_vals = series.dropna().unique()[:5]
                sample_list = [str(x) for x in sample_vals]
                
                # Check for Dates
                if pd.api.types.is_datetime64_any_dtype(series):
                    inferred_type = "Date/Time"
                elif col.lower().endswith("date") or col.lower().endswith("time"):
                    # Try converting a sample to date
                    try:
                        pd.to_datetime(series.dropna().head(5))
                        inferred_type = "Date/Time"
                    except:
                        pass
                
                # Check for ID columns
                if inferred_type == "Text" or pd.api.types.is_integer_dtype(series):
                    if col.lower().endswith("id") or col.lower().endswith("key") or col.lower().endswith("code"):
                        inferred_type = "ID/Key"
                
                # Check for Numeric (Metrics)
                if inferred_type == "Text":
                    if pd.api.types.is_numeric_dtype(series):
                        if unique_val_count > 20 and not col.lower().endswith("id"):
                            inferred_type = "Numeric/Metric"
                        else:
                            inferred_type = "Numeric/Category"
                    elif pd.api.types.is_bool_dtype(series):
                        inferred_type = "Boolean"
                
                # Basic stats
                stats = {}
                if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                    stats = {
                        "min": float(series.min()) if not pd.isna(series.min()) else None,
                        "max": float(series.max()) if not pd.isna(series.max()) else None,
                        "mean": float(series.mean()) if not pd.isna(series.mean()) else None,
                        "std": float(series.std()) if not pd.isna(series.std()) else None
                    }
                elif pd.api.types.is_datetime64_any_dtype(series):
                    stats = {
                        "min": str(series.min()) if not pd.isna(series.min()) else None,
                        "max": str(series.max()) if not pd.isna(series.max()) else None
                    }
                
                # Primary key check candidate
                is_pk_candidate = False
                if unique_val_count == row_count and row_count > 0:
                    is_pk_candidate = True
                
                columns_data.append({
                    "column_name": str(col),
                    "pandas_dtype": str(series.dtype),
                    "inferred_type": inferred_type,
                    "null_count": null_count,
                    "null_pct": null_pct,
                    "unique_values": unique_val_count,
                    "is_pk_candidate": is_pk_candidate,
                    "sample_values": sample_list,
                    "stats": stats
                })
                
            sheets_profile[sheet_name] = {
                "row_count": row_count,
                "col_count": col_count,
                "columns": columns_data
            }
        except Exception as e:
            sheets_profile[sheet_name] = {"error": f"Failed to profile sheet: {str(e)}"}
            
    # Simple relationship heuristics (detect columns with matching names and type classes)
    sheet_names = list(xls.sheet_names)
    for i in range(len(sheet_names)):
        s1 = sheet_names[i]
        if s1 not in all_sheet_cols or "cols" not in all_sheet_cols[s1]:
            continue
        for j in range(i + 1, len(sheet_names)):
            s2 = sheet_names[j]
            if s2 not in all_sheet_cols or "cols" not in all_sheet_cols[s2]:
                continue
            
            # Find matching column names (case-insensitive)
            cols1 = all_sheet_cols[s1]["cols"]
            cols2 = all_sheet_cols[s2]["cols"]
            
            for c1 in cols1:
                for c2 in cols2:
                    if c1.lower() == c2.lower() and (c1.lower().endswith("id") or c1.lower().endswith("key") or c1.lower().endswith("code") or c1.lower().endswith("name")):
                        # Found a possible key link
                        u1 = all_sheet_cols[s1]["unique_counts"][c1]
                        u2 = all_sheet_cols[s2]["unique_counts"][c2]
                        r1 = all_sheet_cols[s1]["row_count"]
                        r2 = all_sheet_cols[s2]["row_count"]
                        
                        # Cardinality guess
                        card1 = "1" if u1 == r1 else "N"
                        card2 = "1" if u2 == r2 else "N"
                        
                        relationship_hints.append({
                            "table1": s1,
                            "column1": c1,
                            "cardinality1": card1,
                            "table2": s2,
                            "column2": c2,
                            "cardinality2": card2,
                            "common_name": c1
                        })
                        
    return {
        "file_name": os.path.basename(file_path),
        "sheets": sheets_profile,
        "relationship_hints": relationship_hints
    }

def format_profile_as_markdown(profile: Dict[str, Any]) -> str:
    """
    Takes the structured profile dict and formats it as a neat markdown string.
    """
    if "error" in profile:
        return f"### Error Profiling File\n{profile['error']}"
        
    md = []
    md.append(f"# Data Profile for `{profile['file_name']}`")
    md.append(f"Analyzed sheets: {', '.join([f'`{s}`' for s in profile['sheets'].keys()])}\n")
    
    for sheet_name, s_data in profile['sheets'].items():
        md.append(f"## Sheet: `{sheet_name}`")
        if "error" in s_data:
            md.append(f"❌ Error: {s_data['error']}\n")
            continue
            
        md.append(f"- **Rows**: {s_data['row_count']}")
        md.append(f"- **Columns**: {s_data['col_count']}\n")
        
        md.append("| Column Name | Inferred Type | Null % | Unique Vals | Primary Key? | Sample Values | Stats |")
        md.append("| --- | --- | --- | --- | --- | --- | --- |")
        
        for col in s_data['columns']:
            pk_str = "Yes (Candidate)" if col['is_pk_candidate'] else "No"
            samples = ", ".join([f"`{val}`" for val in col['sample_values']])
            if len(samples) > 50:
                samples = samples[:47] + "..."
            
            stats_str = ""
            if col['stats']:
                if 'mean' in col['stats'] and col['stats']['mean'] is not None:
                    stats_str = f"Min: {col['stats']['min']:.1f}, Max: {col['stats']['max']:.1f}, Avg: {col['stats']['mean']:.1f}"
                elif 'min' in col['stats'] and col['stats']['min'] is not None:
                    stats_str = f"Min: {col['stats']['min']}, Max: {col['stats']['max']}"
                    
            md.append(f"| {col['column_name']} | {col['inferred_type']} | {col['null_pct']}% | {col['unique_values']} | {pk_str} | {samples} | {stats_str} |")
        md.append("")
        
    if profile.get('relationship_hints'):
        md.append("## Potential Relationship Connections")
        md.append("The profiler detected matching ID/key column names between sheets. These suggest candidate model links:")
        for rel in profile['relationship_hints']:
            md.append(f"- `{rel['table1']}[{rel['column1']}]` ({rel['cardinality1']}) <---> `{rel['table2']}[{rel['column2']}]` ({rel['cardinality2']})")
        md.append("")
        
    return "\n".join(md)

if __name__ == "__main__":
    # Test script if run directly
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"Profiling {filepath}...")
        res = profile_excel_file(filepath)
        print(format_profile_as_markdown(res))
    else:
        print("Usage: python profiler.py <excel_file>")
