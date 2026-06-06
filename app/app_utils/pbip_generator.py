import json
import zipfile
import io
import os

def generate_pbip_zip(schema_json: dict) -> bytes:
    """
    Takes a schema_json dict and returns a zip file containing a basic .pbip structure.
    Returns the zip file as bytes.
    """
    out_zip = io.BytesIO()
    
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Project.pbip
        pbip_content = {
            "version": "1.0",
            "artifacts": [
                {
                    "report": {
                        "path": "Project.Report"
                    }
                },
                {
                    "dataset": {
                        "path": "Project.Dataset"
                    }
                }
            ],
            "settings": {
                "enableAutoRecovery": True
            }
        }
        zf.writestr("Project.pbip", json.dumps(pbip_content, indent=2))
        
        # 2. Dataset configs
        dataset_config = {
            "version": "1.0",
            "logicalId": "00000000-0000-0000-0000-000000000000"
        }
        zf.writestr("Project.Dataset/item.config.json", json.dumps(dataset_config, indent=2))
        
        dataset_metadata = {
            "type": "dataset",
            "displayName": "Project"
        }
        zf.writestr("Project.Dataset/item.metadata.json", json.dumps(dataset_metadata, indent=2))
        
        # 3. Build model.bim from schema_json
        model_bim = {
            "name": "SemanticModel",
            "compatibilityLevel": 1550,
            "model": {
                "culture": "en-US",
                "tables": [],
                "relationships": []
            }
        }
        
        for table in schema_json.get("tables", []):
            bim_table = {
                "name": table.get("name", "Table"),
                "columns": [],
                "measures": []
            }
            
            for col in table.get("columns", []):
                bim_table["columns"].append({
                    "name": col.get("name"),
                    "dataType": col.get("dataType", "string"),
                    "sourceColumn": col.get("name")
                })
                
            for meas in table.get("measures", []):
                bim_table["measures"].append({
                    "name": meas.get("name"),
                    "expression": meas.get("expression")
                })
                
            model_bim["model"]["tables"].append(bim_table)
            
        for rel in schema_json.get("relationships", []):
            model_bim["model"]["relationships"].append({
                "fromTable": rel.get("fromTable"),
                "fromColumn": rel.get("fromColumn"),
                "toTable": rel.get("toTable"),
                "toColumn": rel.get("toColumn"),
                "crossFilteringBehavior": rel.get("crossFilteringBehavior", "bothDirections")
            })
            
        zf.writestr("Project.Dataset/model.bim", json.dumps(model_bim, indent=2))
        
        # 4. Report configs (empty boilerplate to satisfy pbip)
        report_config = {
            "version": "1.0",
            "logicalId": "11111111-1111-1111-1111-111111111111"
        }
        zf.writestr("Project.Report/item.config.json", json.dumps(report_config, indent=2))
        
        report_metadata = {
            "type": "report",
            "displayName": "Project"
        }
        zf.writestr("Project.Report/item.metadata.json", json.dumps(report_metadata, indent=2))
        
        report_json = {
            "config": "{\"name\":\"Report\",\"reportPageCollection\":{\"defaultPage\":{\"name\":\"Page1\"}}}",
            "layoutOptimization": 0
        }
        zf.writestr("Project.Report/report.json", json.dumps(report_json, indent=2))

    return out_zip.getvalue()
