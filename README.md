# LabCalc

LabCalc is a web-based application designed to support DNA labeling experiments by automating calculations and organizing experimental records in a structured way.

## Overview

In DNA–dye labeling experiments, researchers repeatedly perform concentration calculations, reaction planning, and labeling efficiency evaluation.  
LabCalc was developed to replace error-prone manual calculations and spreadsheet-based record management with a more reliable and reproducible workflow.

The application focuses on clarity, traceability, and experimental practicality, rather than full laboratory automation.

## Key Features

- Automatic calculation of DNA–dye reaction conditions  
- Labeling efficiency tracking and comparison  
- Plan-based experiment organization  
- Centralized database for experimental records  
- Spreadsheet-like usability with improved data integrity

## Tech Stack

- **Frontend**: Streamlit  
- **Backend**: Python  
- **Database**: PostgreSQL (Supabase)  

## Installation

Clone the repository and install the required dependencies:

```bash
pip install -r requirements.txt
```
Run the application locally :
```
streamlit run app.py
```

## Usage

1. Register DNA and dye stocks with their concentrations.(menu > Stock DB)
2. Create an experimental plan. (menu > New Reaction)
3. Calculate reaction conditions.(menu > New Reaction)
4. Record labeling results and efficiencies. (menu > Nanodrop > Labeling Efficiency)
5. View reaction records (menu > Plans) and create reaction templates (menu > Templates).
6. Store reagents in your own templates. Only the names of reagents are stored.

The interface is designed to be spreadsheet-like and interactive,  
allowing users to modify parameters and immediately observe updated results.
