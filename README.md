# 📘 HIRA Light – User Guide

This document explains how to update inputs, adjust settings, and generate a new results file.

---

## 1. Files You Will Use

- **Input Workbook:**  
  `HIRA Light (IP) v0.12 (1).xlsx`  
  This is where you update census, resources, and staffing rules.  

- **Config File (optional):**  
  `config/settings.yaml`  
  This is where you adjust **seasons** (low/medium/high months) and **shift definitions** (day/night, hours).  

- **Output Workbook:**  
  `staffing_outputs.xlsx`  
  This file is generated automatically every time you run the program.  
  - If the file is already open, the system will create a new version with a timestamp in the name, for example:  
   "staffing_outputs_20250920_211030.xlsx"

---

## 2. What You Can Update

### a) In the Excel Workbook

- **Census Input (tab)**  
  Update the dates and projected census numbers.  
- **Staffing Grid (tab)**  
  Update RN/NA ratios if they change.  
- **Resource Input (tab)**  
  Update available staff, FTEs, and any leave.  
- **Shifts Input (tab)** (optional)  
  Update or add shift definitions if schedules change.  

### b) In the Config File (YAML)

- **Seasons:**  
  Define which months are *High, Medium, or Low* season.  
- **Shifts:**  
  Define default shifts for RN, NA, or other roles if not using the Excel shift tab.

---

## 3. How to Generate a New Results File

1. Save your changes in the Excel workbook (and/or the YAML file).  
2. Run the program by double-clicking or executing:  

   python main.py

3. The system will process the data and generate a new **output workbook**.

---

## 4. What the Output Contains

The results workbook will include multiple sheets:

- **Summary**  
  Run date, input file used, and row counts for each output.  

- **Staffing Plan**  
  Staff needed by date, role, and season.  

- **Staffing vs Resources**  
  Comparison of staff required vs staff available.  
  - Shortages are highlighted in **red**.  
  - Surpluses are highlighted in **green**.  

- **Staffing Schedule**  
  Assignment of staff to shifts.  

- **Summary by Season**  
  High-level totals grouped by season, role, and shift.  

---

## 5. YAML Config Cheat Sheet

The `config/settings.yaml` file controls **season rules** and **shift definitions**.  

### Example

```yaml
# Define seasons by month and weekday
# weekday: 0=Monday ... 6=Sunday

seasons:
  - months: [6, 7, 8]       # June, July, August
    weekdays: [0,1,2,3,4,5,6]
    season: High

  - months: [12, 1]         # December, January
    weekdays: [0,1,2,3,4,5,6]
    season: Low

  - months: [2,3,4,5,9,10,11]
    weekdays: [0,1,2,3,4]
    season: Medium

  - months: [2,3,4,5,9,10,11]
    weekdays: [5,6]
    season: Low

# Define shifts by role (RN, NA, ED, etc.)
shifts:
  RN:
    - name: Day
      start: "07:00"
      end: "19:00"
      hours: 12
    - name: Night
      start: "19:00"
      end: "07:00"
      hours: 12

  NA:
    - name: Day
      start: "07:00"
      end: "15:00"
      hours: 8
    - name: Evening
      start: "15:00"
      end: "23:00"
      hours: 8
    - name: Night
      start: "23:00"
      end: "07:00"
      hours: 8

  ED:
    - name: Early
      start: "06:00"
      end: "14:00"
      hours: 8
    - name: Mid
      start: "14:00"
      end: "22:00"
      hours: 8
    - name: Night
      start: "22:00"
      end: "06:00"
      hours: 8
```

### Notes

- **Seasons**:  
  - `months` = numeric (1=January … 12=December).  
  - `weekdays` = 0=Monday … 6=Sunday.  
  - `season` = label applied (High, Medium, Low).  

- **Shifts**:  
  - Defined separately per role (RN, NA, ED, etc.).  
  - Each shift has a `name`, `start` time, `end` time, and total `hours`.  

---

## 6. Key Notes

- Always **close the previous results file** before running again.  
- If you forget, the program will create a timestamped copy instead.  
- Only edit **the input workbook** or **the YAML config** — the program handles everything else automatically.  
- You do not need to modify the Python code.  

---

✅ That’s it! Update your input workbook or config, run the program, and collect the new results file.
