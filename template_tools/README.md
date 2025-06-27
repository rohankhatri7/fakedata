# Document Template Generator

This tool helps you generate documents from templates with dynamic data. It's particularly useful for creating mock documents like ID cards, certificates, and forms.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start with Sample Data

1. Clean the sample template and generate a spec file:
   ```bash
   python clean_template.py templates/sample_id_card.png --output-dir output
   ```

2. Generate a document using the sample data:
   ```bash
   python generate_document.py output/sample_id_card_clean.png output/sample_id_card_spec.json data/sample_data.csv --output-dir output/documents
   ```

## Workflow for Your Own Templates

### 1. Create Template Annotations with LabelMe

1. Place your template image in the `templates` directory
2. Launch LabelMe to annotate fields:
   ```bash
   labelme templates/your_template.png
   ```
3. For each field to be filled:
   - Click "Create Polygons" (or press 'Ctrl' + 'R')
   - Draw a polygon around the field
   - Enter a label name (e.g., "fullname", "date_of_birth")
   - Click "Save" (or press 'Ctrl' + 'S') to save the annotations (creates a JSON file)

### 2. Clean the Template

```bash
python clean_template.py templates/your_template.png --output-dir output
```

This will:
- Create a cleaned version of your template with the annotated areas removed
- Generate a `_spec.json` file that maps field names to their positions

### 3. Prepare Your Data

Create a CSV file with column headers matching your field names. For example:

```csv
fullname,date_of_birth,address
"John Doe","01/01/1990","123 Main St"
"Jane Smith","02/02/1995","456 Oak Ave"
```

### 4. Generate Documents

```bash
python generate_document.py output/your_template_clean.png output/your_template_spec.json your_data.csv --output-dir output/documents --count 10
```

This will generate 10 documents using the first 10 rows of your CSV data.
```

This will:
- Create a cleaned version of the template with fields removed
- Generate a JSON spec file with field positions

### 3. Generate Documents

```bash
python generate_document.py output/your_template_clean.png output/your_template_spec.json your_data.csv --output-dir output/documents
```

## Command Line Options

### clean_template.py

```
usage: clean_template.py [-h] [--xml XML] [--output-dir OUTPUT_DIR] template

Clean template and generate spec

positional arguments:
  template              Path to template image

options:
  -h, --help            show this help message and exit
  --xml XML             Path to XML annotation file (default: same as template with .xml extension)
  --output-dir OUTPUT_DIR
                        Output directory
```

### generate_document.py

```
usage: generate_document.py [-h] [--font FONT] [--font-size FONT_SIZE] [--output-dir OUTPUT_DIR] [--row ROW] template spec data

Generate document from template

positional arguments:
  template              Path to cleaned template image
  spec                  Path to template spec JSON
  data                  Path to CSV file with data

options:
  -h, --help            show this help message and exit
  --font FONT           Path to TTF font file
  --font-size FONT_SIZE
                        Base font size
  --output-dir OUTPUT_DIR
                        Output directory
  --row ROW             Row index to use from CSV (0-based)
```

## Example CSV Format

Your CSV file should have column headers that match the field names in your template. For example:

```csv
name,id,dob,issue_date,expiry_date,address
John Doe,ID-12345678,1985-07-15,2023-01-15,2033-01-15,123 Main St, Anytown, NY 12345
Jane Smith,ID-87654321,1990-11-22,2023-02-20,2033-02-20,456 Oak Ave, Somewhere, CA 90210
```

## Notes

- The system uses relative coordinates, so your template can be resized without breaking field positions
- For best results, use high-resolution templates
- The cleaner works best when the background is relatively uniform around the fields to be removed
