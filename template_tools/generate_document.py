import json
import csv
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse

# Font paths
FONTS_DIR = Path(__file__).parent.parent / 'fonts'
DEFAULT_FONT = FONTS_DIR / 'OpenSans_SemiCondensed-Regular.ttf'
SIGNATURE_FONT = FONTS_DIR / 'signature.ttf'

class DocumentGenerator:
    def __init__(self, template_path, spec_path, font_path=None, font_size=12):
        """Initialize the document generator with template and spec"""
        try:
            self.template = Image.open(template_path).convert('RGBA')
            self.spec = self._load_spec(spec_path)
            self.font_path = str(font_path) if font_path else None
            self.font_size = font_size
            self.font_cache = {}
            
            # Set default font if none provided
            if not self.font_path and DEFAULT_FONT.exists():
                self.font_path = str(DEFAULT_FONT)
            
        except Exception as e:
            raise Exception(f"Failed to initialize DocumentGenerator: {str(e)}")
        
    def _load_spec(self, spec_path):
        """Load the template specification"""
        with open(spec_path) as f:
            return json.load(f)
    
    def _get_font(self, field_name, default_size=None):
        """Get font with caching and fallback handling"""
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
    
    def generate(self, data, output_path=None):
        """Generate document with given data"""
        try:
            img = self.template.copy()
            draw = ImageDraw.Draw(img)
            
            for field in self.spec['fields']:
                name = field['name']
                
                # Skip fields named 'blank'
                if name == 'blank':
                    continue
                    
                # Skip signature field here - we'll handle it after regular fields
                if name.lower() == 'signature':
                    continue
                    
                if name not in data:
                    continue
                    
                x, y, w, h = field['bbox']
                value = str(data[name])
                
                # Skip empty values
                if not value.strip():
                    continue
                
                # Convert relative coordinates to absolute
                abs_x = int(x * self.spec['width'])
                abs_y = int(y * self.spec['height'])
                abs_w = int(w * self.spec['width'])
                abs_h = int(h * self.spec['height'])
                
                # Binary search for best font size
                low, high = 6, abs_h * 2  # Start with reasonable bounds
                best_size = 0
                font = None
                
                while low <= high:
                    mid = (low + high) // 2
                    try:
                        font = self._get_font(name, mid)
                        text_bbox = draw.textbbox((0, 0), value, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        if text_width <= abs_w * 0.9 and text_height <= abs_h * 0.9:
                            best_size = mid
                            low = mid + 1  # Try larger font
                        else:
                            high = mid - 1  # Try smaller font
                            
                    except Exception:
                        high = mid - 1  # On error, try smaller font
                
                # Use the best fitting font size
                font_size = best_size if best_size > 0 else 12
                try:
                    font = self._get_font(name, font_size)
                    text_bbox = draw.textbbox((0, 0), value, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    # Center text in the bounding box
                    text_x = abs_x + (abs_w - text_width) // 2
                    text_y = abs_y + (abs_h - text_height) // 2
                    
                    # Draw text
                    draw.text((text_x, text_y), value, font=font, fill=(0, 0, 0, 255))
                    
                except Exception as e:
                    print(f"Failed to render text '{value}': {e}")
            
            # Handle signature field if it exists
            signature_field = next((f for f in self.spec['fields'] if f['name'].lower() == 'signature'), None)
            if signature_field and 'FullName' in data:
                try:
                    x, y, w, h = signature_field['bbox']
                    abs_x = int(x * self.spec['width'])
                    abs_y = int(y * self.spec['height'])
                    abs_w = int(w * self.spec['width'])
                    abs_h = int(h * self.spec['height'])
                    
                    # Get signature text (use FullName from data)
                    signature_text = data['FullName']
                    
                    # Calculate maximum font size that fits the width with some padding
                    max_font_size = min(72, abs_h)  # Start with a reasonable max size
                    min_font_size = 6
                    best_size = min_font_size
                    
                    # Try with signature font first
                    try:
                        # Binary search for best font size
                        low = min_font_size
                        high = max_font_size
                        
                        while low <= high:
                            mid = (low + high) // 2
                            try:
                                font = ImageFont.truetype(str(SIGNATURE_FONT), mid)
                                text_width = draw.textlength(signature_text, font=font)
                                
                                if text_width <= abs_w * 0.9:  # 90% of width to add some padding
                                    best_size = mid
                                    low = mid + 1
                                else:
                                    high = mid - 1
                            except Exception:
                                high = mid - 1
                        
                        # Use the best fitting font size
                        sig_font = ImageFont.truetype(str(SIGNATURE_FONT), best_size)
                        
                        # Draw the signature with left alignment and slight vertical adjustment (move up by 10%)
                        text_bbox = draw.textbbox((0, 0), signature_text, font=sig_font)
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        # Position signature with left alignment and slight vertical adjustment
                        text_x = abs_x + 5  # Small left padding
                        text_y = abs_y + (abs_h - text_height) // 2 - int(abs_h * 0.1)  # Move up slightly
                        
                        draw.text((text_x, text_y), signature_text, font=sig_font, fill=(0, 0, 0, 255))
                        
                    except Exception as e:
                        print(f"Could not use signature font, falling back to italic: {e}")
                        # Fallback to italic text if signature font fails
                        font = ImageFont.truetype(str(DEFAULT_FONT), min(14, abs_h))
                        font = font.font_variant(style='italic')
                        text_bbox = draw.textbbox((0, 0), signature_text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        # Scale font to fit width if needed
                        if text_width > abs_w * 0.9:  # 90% of width
                            scale_factor = (abs_w * 0.9) / text_width
                            font_size = int(min(14, abs_h) * scale_factor)
                            font = ImageFont.truetype(str(DEFAULT_FONT), max(6, font_size))
                            font = font.font_variant(style='italic')
                            text_bbox = draw.textbbox((0, 0), signature_text, font=font)
                            text_height = text_bbox[3] - text_bbox[1]
                        
                        # Position signature with left alignment and slight vertical adjustment
                        text_x = abs_x + 5  # Small left padding
                        text_y = abs_y + (abs_h - text_height) // 2 - int(abs_h * 0.1)  # Move up slightly
                        
                        draw.text((text_x, text_y), signature_text, font=font, fill=(0, 0, 0, 255))
                
                except Exception as e:
                    print(f"Failed to render signature: {e}")
            
            # Save or return the image
            if output_path:
                img.save(output_path)
                return output_path
            return img

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
    parser.add_argument('doc_type', help='Document type (e.g., passport, paystub)')
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
    
    # Build file paths
    cleaned_template = base_dir / 'output' / f"{args.doc_type}_clean.png"
    spec_file = base_dir / 'output' / f"{args.doc_type}_spec.json"
    data_file = Path(args.data)
    
    # Check if files exist
    if not cleaned_template.exists():
        print(f"ERROR: Cleaned template not found: {cleaned_template}")
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
        # Initialize generator
        generator = DocumentGenerator(cleaned_template, spec_file, args.font, args.font_size)
        
        # Load data
        with open(data_file) as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        if not data:
            print("ERROR: No data found in the CSV file")
            return
            
        # Limit number of documents if count is specified
        count = min(args.count, len(data)) if args.count else len(data)
        
        if args.count and args.count > len(data):
            print(f"Only {len(data)} rows available, generating {count} documents")
        
        # Generate documents
        if count > 1:
            generated_files = generate_batch(generator, data[:count], output_dir, count)
            print("\nGenerated documents:")
            for i, file_path in enumerate(generated_files, 1):
                print(f"  {i}. {file_path}")
        else:
            # Single document
            output_path = output_dir / f"{args.doc_type}1.png"
            generator.generate(data[0], output_path=output_path)
            print(str(output_path))
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
