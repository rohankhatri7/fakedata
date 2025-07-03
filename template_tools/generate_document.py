import json
import csv
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse
import random

FONTS_DIR = Path(__file__).parent.parent / 'fonts'
DEFAULT_FONT = FONTS_DIR / 'OpenSans_SemiCondensed-Regular.ttf'
SIGNATURE_FONT = FONTS_DIR / 'signature.ttf'

# Map base document types to their available subtypes
DOCUMENT_SUBTYPES = {
    'passport': ['us_passport', 'india_passport'],
    'paystub': ['adp_paystub', 'paychex_paystub'],
    'ssn': ['us_ssn'],  # example – extend as needed
}


class DocumentGenerator:
    def __init__(self, template_path, spec_path, font_path=None, font_size=12):
        try:
            self.template = Image.open(template_path).convert('RGBA')
            self.spec = self._load_spec(spec_path)
            self.font_path = str(font_path) if font_path else None
            self.font_size = font_size
            self.font_cache = {}
            
            if not self.font_path and DEFAULT_FONT.exists():
                self.font_path = str(DEFAULT_FONT)
            
        except Exception as e:
            raise Exception(f"Failed to initialize DocumentGenerator: {str(e)}")
        
    def _load_spec(self, spec_path):
        with open(spec_path) as f:
            return json.load(f)
    
    def _get_font(self, field_name, default_size=None):
        size = default_size or self.font_size
        cache_key = f"{field_name}_{size}"
        
        if cache_key not in self.font_cache:
            try:
                if self.font_path and os.path.exists(self.font_path):
                    try:
                        font = ImageFont.truetype(self.font_path, size)
                        self.font_cache[cache_key] = font
                    except Exception as e:
                        print(f"Could not load specified font {self.font_path}: {e}")
                        raise
                else:
                    raise FileNotFoundError("No font path provided")
            except Exception as e:
                print(f"Could not load font: {e}. Using default font.")
                self.font_cache[cache_key] = ImageFont.load_default()
                    
        return self.font_cache[cache_key]
    
    def _composite_on_a4(self, img):
        """Composite the document onto an A4 page with random positioning and scaling"""
        try:
            # Path to blank page template
            blank_path = Path(__file__).parent / 'templates' / 'blank.png'
            if not blank_path.exists():
                print(f"Warning: A4 template not found at {blank_path}")
                return img.convert('L').convert('RGBA')

            a4_img = Image.open(blank_path).convert('RGBA')
            a4_width, a4_height = a4_img.size
            
            # Convert document to grayscale
            if img.mode != 'L':
                img = img.convert('L').convert('RGBA')
            
            # Compute maximum width/height available after margins
            margin = int(min(a4_width, a4_height) * 0.05)
            max_w_avail = a4_width - 2 * margin
            max_h_avail = a4_height - 2 * margin

            # Random scale between 60% and 100% of the available space (never exceeding page)
            max_scale_w = max_w_avail / img.width
            max_scale_h = max_h_avail / img.height
            max_scale   = min(max_scale_w, max_scale_h, 1.0)
            # pick scale between 60% and 90% of the maximum achievable
            upper = max_scale * 0.9  # up to 90% of max possible
            lower = max_scale * 0.6  # down to 60% of max possible
            if lower > upper:
                lower = upper * 0.9  # fallback: very close to max if needed
            scale = random.uniform(lower, upper)

            new_size = (int(img.width * scale), int(img.height * scale))
            max_width = int(a4_width * 0.9)
            min_width = int(a4_width * 0.6)
            target_width = random.randint(min_width, max_width)
            
            # Resize keeping aspect ratio
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Random position respecting margins
            x = random.randint(margin, a4_width - img.width - margin)
            y = random.randint(margin, a4_height - img.height - margin)
            
            # Composite onto A4
            a4_img.paste(img, (x, y), img if img.mode == 'RGBA' else None)
            
            return a4_img.convert('L').convert('RGBA')  # Ensure grayscale output
            
        except Exception as e:
            print(f"Error during A4 composition: {e}")
            return img.convert('L').convert('RGBA')  # Fallback to grayscale
            
    def generate(self, data, output_path=None):
        try:
            img = self.template.copy()
            draw = ImageDraw.Draw(img)
            
            for field in self.spec['fields']:
                name = field['name']
                
                if name == 'blank':
                    continue
                    
                if name.lower() == 'signature':
                    continue
                    
                x, y, w, h = field['bbox']
                
                if w <= 0 or h <= 0:
                    continue
                # convert labelme coords to absolute
                abs_x = int(x * self.spec['width'])
                abs_y = int(y * self.spec['height'])
                abs_w = int(w * self.spec['width'])
                abs_h = int(h * self.spec['height'])
                
                # Handle multiple fields in one label (comma-separated)
                field_names = [n.strip() for n in field['name'].split(',')]
                
                # Group City and State together if they appear consecutively
                processed_fields = []
                i = 0
                while i < len(field_names):
                    if field_names[i] == 'City' and i + 1 < len(field_names) and field_names[i+1] == 'State':
                        processed_fields.append(('City,State', i, i+1))
                        i += 2
                    else:
                        processed_fields.append((field_names[i], i, i))
                        i += 1
                
                field_values = []
                for field_info in processed_fields:
                    field_name, start_idx, end_idx = field_info
                    
                    if field_name == 'City,State':
                        # Get both City and State values
                        city = str(data.get('City', '')).strip()
                        state = str(data.get('State', '')).strip()
                        if city and state:
                            value = f"{city}, {state}"
                        else:
                            value = city or state
                        if value:
                            field_values.append(value)
                    else:
                        value = str(data.get(field_name, '')).strip()
                        if value:
                            field_values.append(value)
                
                if not field_values:
                    continue
                
                max_font_size = 72
                best_size = 0
                
                for size in range(12, max_font_size + 1):
                    try:
                        font = self._get_font(name, size)
                        total_height = 0
                        max_width = 0
                        
                        for value in field_values:
                            bbox = draw.textbbox((0, 0), value, font=font)
                            total_height += (bbox[3] - bbox[1]) * 1.08  # 8% spacing
                            max_width = max(max_width, bbox[2] - bbox[0])
                        
                        if total_height <= abs_h * 0.9 and max_width <= abs_w * 0.9:
                            best_size = size
                        else:
                            break
                            
                    except Exception:
                        break
                        
                if best_size > 0:
                    try:
                        font = self._get_font(name, best_size)
                        y_offset = 0  
                        
                        for value in field_values:
                            if value:
                                text_bbox = draw.textbbox((0, 0), value, font=font)
                                text_width = text_bbox[2] - text_bbox[0]
                                text_height = text_bbox[3] - text_bbox[1]
                                
                                text_x = abs_x + 2  
                                text_y = abs_y + y_offset
                                
                                draw.text((text_x, text_y), value, font=font, fill=(0, 0, 0, 255))
                                
                                y_offset += text_height * 1.08  # 8% spacing between lines
                        
                    except Exception:
                        pass 
            
            signature_field = next((f for f in self.spec['fields'] if f['name'].lower() == 'signature'), None)
            if signature_field and 'FullName' in data:
                try:
                    x, y, w, h = signature_field['bbox']
                    abs_x = int(x * self.spec['width'])
                    abs_y = int(y * self.spec['height'])
                    abs_w = int(w * self.spec['width'])
                    abs_h = int(h * self.spec['height'])
                    
                    signature_text = data['FullName']
                    
                    max_font_size = min(72, abs_h)
                    min_font_size = 6
                    best_size = min_font_size
                    
                    try:
                        # Binary search for best font size
                        low = min_font_size
                        high = max_font_size
                        
                        while low <= high:
                            mid = (low + high) // 2
                            try:
                                font = ImageFont.truetype(str(SIGNATURE_FONT), mid)
                                text_width = draw.textlength(signature_text, font=font)
                                
                                if text_width <= abs_w * 0.9:
                                    best_size = mid
                                    low = mid + 1
                                else:
                                    high = mid - 1
                            except Exception:
                                high = mid - 1
                        
                        sig_font = ImageFont.truetype(str(SIGNATURE_FONT), best_size)
                        
                        text_bbox = draw.textbbox((0, 0), signature_text, font=sig_font)
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        text_x = abs_x + 5
                        text_y = abs_y + 2
                        
                        draw.text((text_x, text_y), signature_text, font=sig_font, fill=(0, 0, 0, 255))
                        
                    except Exception as e:
                        print(f"Could not use signature font, falling back to italic: {e}")
                        font = ImageFont.truetype(str(DEFAULT_FONT), min(14, abs_h))
                        font = font.font_variant(style='italic')
                        text_bbox = draw.textbbox((0, 0), signature_text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        if text_width > abs_w * 0.9:
                            scale_factor = (abs_w * 0.9) / text_width
                            font_size = int(min(14, abs_h) * scale_factor)
                            font = ImageFont.truetype(str(DEFAULT_FONT), max(6, font_size))
                            font = font.font_variant(style='italic')
                            text_bbox = draw.textbbox((0, 0), signature_text, font=font)
                            text_height = text_bbox[3] - text_bbox[1]
                        
                        text_x = abs_x + 5
                        text_y = abs_y + 2
                        
                        draw.text((text_x, text_y), signature_text, font=font, fill=(0, 0, 0, 255))
                
                except Exception as e:
                    print(f"Failed to render signature: {e}")
            
            # Save or return the image
            # Composite onto A4 before saving
            final_img = self._composite_on_a4(img)
            
            if output_path:
                final_img.save(output_path, 'PNG', quality=95, dpi=(300, 300))
            
            return final_img

        except Exception as e:
            print(f"Failed to generate document: {e}")

def generate_batch(generator, data_list, output_dir, count=None):
    """Generate multiple documents from a list of data dictionaries"""
    if not data_list:
        print("No data provided for document generation")
        return []
        
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Limit to requested count or all available data
    count = min(count, len(data_list)) if count else len(data_list)
    
    generated_files = []
    for i in range(count):
        output_path = output_dir / f"document{i+1}.png"
        try:
            generator.generate(data_list[i], output_path=output_path)
            generated_files.append(str(output_path))
        except Exception as e:
            print(f"Error generating document {i+1}: {e}")
    
    return generated_files

def main():
    parser = argparse.ArgumentParser(description='Generate documents from template and data')
    parser.add_argument('doc_type', help='Document type base (passport, paystub, ssn) or specific subtype (e.g., us_passport)')
    parser.add_argument('--subtype', help='Explicit subtype to use (e.g., us_passport). Overrides random choice.')
    parser.add_argument('--no-random', action='store_true', help='Disable random subtype selection when base doc_type is given')
    parser.add_argument('--data', default='data/sample_data.csv', help='Path to CSV data file (default: data/sample_data.csv)')
    parser.add_argument('--output-dir', default='output/documents', help='Output directory (default: output/documents)')
    parser.add_argument('--font', help='Path to custom font file')
    parser.add_argument('--font-size', type=int, default=12, help='Base font size (default: 12)')
    parser.add_argument('--count', type=int, help='Number of documents to generate (default: all rows in CSV)')
    
    args = parser.parse_args()
    
    # Set up paths
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates'
    output_dir = Path(args.output_dir)
    
    # Resolve subtype(s)
    if '_' in args.doc_type:
        # User already passed a full subtype
        base_type = args.doc_type.split('_')[-1]
        subtype_list = [args.doc_type]
    else:
        base_type = args.doc_type.lower()
        subtype_list = DOCUMENT_SUBTYPES.get(base_type)
        if not subtype_list:
            print(f"ERROR: Unknown document type '{args.doc_type}'. Available: {list(DOCUMENT_SUBTYPES.keys())}")
            return
    
    # Validate explicit subtype
    if args.subtype:
        if args.subtype not in subtype_list:
            print(f"ERROR: Subtype '{args.subtype}' not valid for base type '{base_type}'. Choose from: {subtype_list}")
            return
        subtype_list = [args.subtype]
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    data_file = Path(args.data)
    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        return
    with open(data_file) as f:
        reader = csv.DictReader(f)
        data_rows = list(reader)
    if not data_rows:
        print("ERROR: No data found in the CSV file")
        return
    
    # Determine how many docs to generate
    max_docs = len(data_rows)
    count = min(args.count, max_docs) if args.count else max_docs
    if args.count and args.count > max_docs:
        print(f"Only {max_docs} rows available, generating {count} documents")

    # Choose a single subtype for this batch
    if len(subtype_list) == 1:
        chosen_subtype = subtype_list[0]
    else:
        chosen_subtype = subtype_list[0] if args.no_random else random.choice(subtype_list)
        print(f"Randomly selected subtype: {chosen_subtype}")

    cleaned_template = base_dir / 'output' / 'clean_templates' / f"{chosen_subtype}_clean.png"
    spec_file       = base_dir / 'output' / 'clean_templates' / f"{chosen_subtype}_spec.json"
    if not cleaned_template.exists() or not spec_file.exists():
        print(f"ERROR: Cleaned assets for '{chosen_subtype}' not found. Run 'python clean_template.py {chosen_subtype}' first.")
        return

    # Create generator once
    generator = DocumentGenerator(cleaned_template, spec_file, args.font, args.font_size)

    generated_files = []
    for i in range(count):
        if not cleaned_template.exists() or not spec_file.exists():
            print(f"Skipping {subtype}: cleaned assets missing. Run 'python clean_template.py {subtype}' first.")
            continue
        
        try:
            output_path = output_dir / f"{chosen_subtype}_{i+1}.png"
            generator.generate(data_rows[i], output_path=output_path)
            generated_files.append(str(output_path))
        except Exception as e:
            print(f"Error generating document {i+1} ({chosen_subtype}): {e}")

    # Summary
    if generated_files:
        print("\nGenerated documents:")
        for idx, fp in enumerate(generated_files, 1):
            print(f"  {idx}. {fp}")
    else:
        print("No documents generated due to previous errors.")
    cleaned_template = base_dir / 'output' / 'clean_templates' / f"{args.doc_type}_clean.png"
    spec_file = base_dir / 'output' / 'clean_templates' / f"{args.doc_type}_spec.json"
    data_file = Path(args.data)
    
    # Check if files exist
    if not cleaned_template.exists():

        print(f"Please run 'python clean_template.py {args.doc_type}' first")
        return
        
    if not spec_file.exists():
        print(f"ERROR: Spec file not found: {spec_file}")
        print(f"Please run 'python clean_template.py {args.doc_type}' first")
        return
        
    if not data_file.exists():
        print(f"ERROR: Data file not found: {data_file}")
        print("Please provide a valid CSV file with --data")
        return
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        generator = DocumentGenerator(cleaned_template, spec_file, args.font, args.font_size)
        
        with open(data_file) as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        if not data:
            print("ERROR: No data found in the CSV file")
            return
            
        count = min(args.count, len(data)) if args.count else len(data)
        
        if args.count and args.count > len(data):
            print(f"Only {len(data)} rows available, generating {count} documents")
        
        if count > 1:
            generated_files = generate_batch(generator, data[:count], output_dir, count)
            print("\nGenerated documents:")
            for i, file_path in enumerate(generated_files, 1):
                print(f"  {i}. {file_path}")
        else:
            output_path = output_dir / f"{args.doc_type}1.png"
            generator.generate(data[0], output_path=output_path)
            print(str(output_path))
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
