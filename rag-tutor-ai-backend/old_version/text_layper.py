from langchain_community.document_loaders import PyPDFLoader

# Try to load the file from your temp folder
file_to_test = "temp_compressed/Tan_Chung_India-and-China.pdf"
loader = PyPDFLoader(file_to_test)
pages = loader.load()

print(f"--- Diagnostic for: {file_to_test} ---")
print(f"Total Pages Found: {len(pages)}")

if len(pages) > 0:
    first_page_text = pages[0].page_content.strip()
    print(f"Characters found on Page 1: {len(first_page_text)}")
    if len(first_page_text) == 0:
        print("❌ RESULT: Page found but it is EMPTY. This is a scanned image PDF.")
    else:
        print(f"✅ RESULT: Text found! First 50 chars: {first_page_text[:50]}")
else:
    print("❌ RESULT: No pages could be loaded at all.")
