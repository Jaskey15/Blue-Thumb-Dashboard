import pathlib
import re
import shutil
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from layouts.ui_data import (
    CHEMICAL_DIAGRAM_CAPTIONS,
    COMMUNITY_CARDS,
    FISH_DATA,
    HABITAT_DIAGRAM_CAPTIONS,
    HOME_YARD_CARDS,
    MACRO_DATA,
    RECREATION_CARDS,
    RURAL_CARDS,
)

TEXT_DIR = PROJECT_ROOT / "text"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "chatbot_data"

def sanitize_filename(name):
    """Sanitizes a name to be a valid filename."""
    sanitized = name.lower()
    sanitized = re.sub(r'[\s/&]+', '-', sanitized)
    sanitized = re.sub(r'[^\w\-.]', '', sanitized)
    return sanitized

def process_markdown_files():
    """Processes all markdown files from the text directory."""
    print("Processing markdown files...")
    md_files = list(TEXT_DIR.glob("**/*.md"))
    for md_file in md_files:
        shutil.copy(md_file, OUTPUT_DIR / md_file.name)
    print(f"-> Copied {len(md_files)} markdown files.")

def process_action_cards():
    """Processes action cards from ui_data.py."""
    print("Processing action cards...")
    all_cards = {
        "home_yard": HOME_YARD_CARDS,
        "rural_ag": RURAL_CARDS,
        "recreation": RECREATION_CARDS,
        "community": COMMUNITY_CARDS
    }
    
    count = 0
    for category, cards in all_cards.items():
        for card in cards:
            title = card.get("title", "untitled")
            why_text = card.get("why_text", "")
            tips = card.get("tips_list", [])

            content = f"Category: {category.replace('_', ' ').title()}\n"
            content += f"Title: {title}\n\n"
            content += f"Why this is important: {why_text}\n\n"
            if tips:
                content += "Tips:\n"
                for tip in tips:
                    content += f"- {tip}\n"
            
            filename = "action-card-" + sanitize_filename(title) + ".txt"
            with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            
    print(f"-> Created {count} files from action cards.")

def process_species_data():
    """Processes species descriptions from ui_data.py."""
    print("Processing species data...")
    species_count = 0
    
    for item in FISH_DATA:
        name = item.get("name")
        description = item.get("description")
        if name and description:
            content = f"Species Type: Fish\n"
            content += f"Name: {name}\n\n"
            content += f"Description: {description}"
            filename = "species-" + sanitize_filename(name) + ".txt"
            with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
                f.write(content)
            species_count += 1

    for item in MACRO_DATA:
        name = item.get("name")
        description = item.get("description")
        if name and description:
            content = f"Species Type: Macroinvertebrate\n"
            content += f"Name: {name}\n\n"
            content += f"Description: {description}"
            filename = "species-" + sanitize_filename(name) + ".txt"
            with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
                f.write(content)
            species_count += 1
            
    print(f"-> Created {species_count} files from species data.")

def process_diagram_captions():
    """Processes diagram captions from ui_data.py."""
    print("Processing diagram captions...")
    all_captions = {
        "Chemical Diagram": CHEMICAL_DIAGRAM_CAPTIONS,
        "Habitat Diagram": HABITAT_DIAGRAM_CAPTIONS
    }
    
    caption_count = 0
    for category, captions in all_captions.items():
        for key, caption_text in captions.items():
            content = f"Category: {category}\n"
            content += f"Topic: {key.replace('_', ' ').title()}\n\n"
            content += f"Caption: {caption_text}"
            
            filename = "caption-" + sanitize_filename(key) + ".txt"
            with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
                f.write(content)
            caption_count += 1
            
    print(f"-> Created {caption_count} files from diagram captions.")

def main():
    """Main function to prepare all chatbot context data."""
    print(f"Output directory: {OUTPUT_DIR}")
    
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    
    print("\nStarting data preparation...")
    process_markdown_files()
    process_action_cards()
    process_species_data()
    process_diagram_captions()
    print("\nData preparation complete.")
    print(f"All context files have been saved to:\n{OUTPUT_DIR.resolve()}")

if __name__ == "__main__":
    main() 