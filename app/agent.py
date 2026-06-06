import os
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.apps import App
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Load environment variables (such as GOOGLE_API_KEY)
load_dotenv()

# We use the standard gemini-3-flash-preview model for high-speed agent execution and better rate limits.
def get_model():
    return Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    )

def exit_loop():
    """Call this tool when the output meets all quality and accuracy requirements to break out of the loop."""
    return "EXIT"

def create_data_profiler():
    return Agent(
        name="data_profiler",
        model=get_model(),
        instruction="""You are Agent 1 - Data Profiler. Your task is to perform a deep analysis of the Excel data profile and align it with the user's business goals.
Initial User Intention: {user_prompt}
Excel Data Profile: {excel_profile}

Based on the provided Excel profile:
1. Provide a detailed summary of the dataset (sheets, row/col count, major columns).
2. Identify data quality issues (such as nulls, improper dates, un-normalized repeating values).
3. Identify candidates for fact tables (transaction/metric sheets) and dimension tables (lookup tables like customer, products, dates).
4. Propose data cleaning and transformation steps that the user must take in Power Query (e.g. splitting columns, filtering null rows, changing column data types).

Make your analysis concrete. Directly reference the sheets and columns from the Excel profile. Do not output generic advice.
""",
        output_key="data_profiler_output"
    )

def create_model_architect():
    return Agent(
        name="model_architect",
        model=get_model(),
        instruction="""You are Agent 2 - Model Architect. Your task is to design the optimal Power BI data model based on the Data Profiler's analysis and the user's goals.
Initial User Intention: {user_prompt}
Data Profiler Output: {data_profiler_output}

Design the model schema:
1. Clearly specify Table Mappings: list which tables are Fact tables and which are Dimension tables.
2. Outline all Relationships: table relationships including key columns, relationship types (one-to-many 1:*), filter direction, and cross-filter setting.
3. Draw a Mermaid relationship diagram showing the tables and how they link.
   Format rules for Mermaid:
   - Use standard flowchart syntax (e.g., `graph TD` or `erDiagram`).
   - Wrap table and column names in quotes to avoid syntax errors (e.g. `FactSales["FactSales"] -->|"1:*"| DimCustomers["DimCustomers"]`).
4. Suggest column data types, hierarchies, and sort-by columns (e.g., "Sort column 'Month Name' by 'Month Number' in the Column Tools tab").

Ensure your schema directly models the data described in the profiler output.
""",
        output_key="model_architect_output"
    )

def create_dax_engineer():
    return Agent(
        name="dax_engineer",
        model=get_model(),
        instruction="""You are Agent 3 - DAX Engineer. Your task is to write clean, optimized, and correct DAX formulas to meet the user's business goals.
Initial User Intention: {user_prompt}
Model Architect Output: {model_architect_output}

Write DAX calculations (Measures, Calculated Columns, or Calculated Tables) based on the model layout.
For each calculation:
1. Specify its Type (e.g., Measure, Calculated Column, Calculated Table).
2. Give it a clear business name.
3. Provide the exact DAX code in a markdown block.
4. Specify where to paste it in Power BI Desktop (e.g. "Select table Sales, click Modeling tab -> New Measure").
5. Provide a short explanation of how the formula works.

Use standard Power BI DAX formatting. Reference the exact table and column names designed by the Model Architect.
""",
        output_key="dax_engineer_output"
    )

def create_tmdl_specialist():
    return Agent(
        name="tmdl_specialist",
        model=get_model(),
        instruction="""You are Agent 4 - TMDL Specialist. Your task is to provide Tabular Model Definition Language (TMDL) scripts or Tabular Editor C# scripts for advanced automation.
Initial User Intention: {user_prompt}
Model Architect Output: {model_architect_output}
DAX Engineer Output: {dax_engineer_output}

Write a TMDL script or a C# scripting block for Tabular Editor to automate the creation of:
1. The DAX measures designed by the DAX Engineer.
2. Or lookup tables/calculated tables.

Provide:
1. The script code block.
2. Simple, step-by-step instructions on where to run it (e.g., "Open Tabular Editor -> Advanced Scripting tab -> paste script -> run").
If TMDL automation is not suited for this simple model, provide a helpful explanation of TMDL scripting and how the user can export their model to TMDL files in Power BI Desktop.
""",
        output_key="tmdl_specialist_output"
    )

def create_ux_advisor():
    return Agent(
        name="ux_advisor",
        model=get_model(),
        instruction="""You are Agent 5 - UX Advisor. Your task is to design report page layouts and visual interaction patterns for the Power BI report.
Initial User Intention: {user_prompt}
Model Architect Output: {model_architect_output}
DAX Engineer Output: {dax_engineer_output}

Recommend:
1. Page structure and grid layouts (e.g., Executive Summary page, Detail analysis page).
2. Visual visual selections (e.g., line chart for monthly sales trends, matrix for sales breakdown by categories, cards for KPIs).
3. Interactivity: slicers, drill-through actions, bookmarks, tooltips, and parameter setups.
4. Best practices for clean and premium design (typography, alignment, visual hierarchy).
""",
        output_key="ux_advisor_output"
    )

def create_final_compiler():
    return Agent(
        name="final_compiler",
        model=get_model(),
        instruction="""You are the Orchestrator Compiler. Your job is to compile the outputs of all specialized agents into a single, cohesive, premium developer report.

Data Profiler Summary:
{data_profiler_output}

Model Design:
{model_architect_output}

DAX Calculations:
{dax_engineer_output}

TMDL / Scripting Automation:
{tmdl_specialist_output}

UX & Visual Guidelines:
{ux_advisor_output}

Format the final output EXACTLY in this Markdown structure:

## 1. Data Analysis Summary  
[Include the findings about the Excel file, quality issues, and recommended cleaning steps]  

## 2. Power BI Model Design  
[Include Fact vs Dimension mappings, hierarchies, and the Mermaid diagram]  

## 3. DAX Code to Paste  
[Include calculated measures and columns, with the exact location to paste them]  

## 4. TMDL Code (if applicable)  
[Include TMDL scripts and Tabular Editor advanced scripting blocks]  

## 5. Step-by-Step Instructions  
[A numbered checklist from loading Excel files, importing data, establishing relationships, writing DAX, to report publishing]  

## 6. Limitations & Recommendations  
[Mention constraints, calculated columns vs. measures performance details, import/DirectQuery mode notes, and data scale limits]

Ensure the output is clean, highly readable, structured, and contains no placeholders. Keep a highly professional and encouraging tone. Do not include variables or internal agent logs.
""",
        output_key="final_output"
    )

def create_schema_json_generator():
    return Agent(
        name="schema_json_generator",
        model=get_model(),
        instruction="""You are the Schema JSON Generator.
Your job is to read the agent outputs and generate a pure JSON object representing the Power BI schema for the `.pbip` project generator.
Output ONLY valid JSON, no markdown formatting or extra text. If you must use a code block, use ```json.

Data Profiler Summary:
{data_profiler_output}

Model Design:
{model_architect_output}

DAX Calculations:
{dax_engineer_output}

The JSON MUST match this structure exactly:
{
  "tables": [
    {
      "name": "TableName",
      "columns": [
        {"name": "Col1", "dataType": "string"},
        {"name": "Col2", "dataType": "int64"}
      ],
      "measures": [
        {"name": "Measure1", "expression": "SUM(Table[Col])"}
      ]
    }
  ],
  "relationships": [
    {
      "fromTable": "FactSales",
      "fromColumn": "DateKey",
      "toTable": "DimDate",
      "toColumn": "DateKey",
      "crossFilteringBehavior": "bothDirections"
    }
  ]
}
Make sure all table and column names correspond to the model.
""",
        output_key="schema_json"
    )

def create_quality_auditor():
    return Agent(
        name="quality_auditor",
        model=get_model(),
        instruction="""You are the Quality Auditor. Review the generated documentation and schema json against the user's requirements.
Initial User Intention: {user_prompt}
Current Document: {final_output}
Current Schema JSON: {schema_json}

Check for:
1. All DAX expressions reference valid columns/tables.
2. Relationships are logical.
3. Schema JSON perfectly maps to the documentation.
4. User intent is fully satisfied.

If there are issues, provide a detailed explanation of what is wrong and what needs fixing. Do NOT call exit_loop.
If everything is perfect and flawless, CALL the exit_loop tool immediately to finish.
""",
        tools=[exit_loop],
        output_key="audit_feedback"
    )

def create_refiner():
    return Agent(
        name="refiner",
        model=get_model(),
        instruction="""You are the Refiner. You receive feedback from the Quality Auditor and must update the Final Document and Schema JSON accordingly.
Audit Feedback: {audit_feedback}
Current Document: {final_output}
Current Schema JSON: {schema_json}

Fix the errors mentioned in the feedback.
First, output the corrected Final Document.
Then, output the corrected Schema JSON enclosed in a ```json codeblock at the very end of your response.
Make sure you include everything, even the parts that did not change.
""",
        output_key="final_output" # This overwrites final_output for the next loop iteration or final result
    )

# The generation sequence
generation_agent = SequentialAgent(
    name="generation_agent",
    sub_agents=[
        create_data_profiler(),
        create_model_architect(),
        create_dax_engineer(),
        create_tmdl_specialist(),
        create_ux_advisor(),
        create_final_compiler(),
        create_schema_json_generator(),
    ]
)

# The refinement loop
refinement_loop = LoopAgent(
    name="refinement_loop",
    sub_agents=[
        create_quality_auditor(),
        create_refiner()
    ],
    max_iterations=3
)

# root_agent pipes the generation output to the refinement loop
root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[
        generation_agent,
        refinement_loop
    ]
)

app = App(
    root_agent=root_agent,
    name="powerbi_developer_system",
)
