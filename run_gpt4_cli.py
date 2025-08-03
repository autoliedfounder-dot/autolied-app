
import sys
from run_gpt4 import process_sheet_music_with_gpt4

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: run_gpt4_cli.py <input_pdf> <output_pptx> <title> <api_key>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_pptx = sys.argv[2]
    title = sys.argv[3]
    api_key = sys.argv[4]
    
    try:
        process_sheet_music_with_gpt4(
            pdf_path=input_pdf,
            output_pptx=output_pptx,
            api_key=api_key,
            title=title,
            max_lines_per_slide=1,
            export_text=True
        )
        print("Success")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
