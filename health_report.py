import os
import glob
from bs4 import BeautifulSoup
from collections import defaultdict

STATIC_DIR = 'static'

def generate_report():
    html_files = glob.glob(os.path.join(STATIC_DIR, '**/*.html'), recursive=True)
    
    # Valid paths (clean URLs mapped back to paths)
    valid_paths = set(['/'])
    for filepath in html_files:
        rel_path = filepath.replace(STATIC_DIR, '').replace('.html', '').replace('\\', '/')
        if rel_path == '/index':
            valid_paths.add('/')
        else:
            valid_paths.add(rel_path)
            
    report = {
        'total_pages': len(html_files),
        'missing_title': [],
        'missing_desc': [],
        'missing_canonical': [],
        'missing_h1': [],
        'multiple_h1': [],
        'missing_alt': [],
        'broken_links': defaultdict(list)
    }

    for filepath in html_files:
        if '.bak' in filepath: continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'html.parser')
            except Exception as e:
                print(f"Failed to parse {filepath}: {e}")
                continue
        
        short_name = filepath.replace(STATIC_DIR + '/', '')
            
        # Title
        if not soup.title or not soup.title.string or soup.title.string.strip() == '':
            report['missing_title'].append(short_name)
            
        # Meta description
        desc = soup.find('meta', attrs={'name': 'description'})
        if not desc or not desc.get('content') or desc.get('content').strip() == '':
            report['missing_desc'].append(short_name)
            
        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if not canonical or not canonical.get('href') or canonical.get('href').strip() == '':
            report['missing_canonical'].append(short_name)
            
        # H1
        h1s = soup.find_all('h1')
        if len(h1s) == 0:
            report['missing_h1'].append(short_name)
        elif len(h1s) > 1:
            report['multiple_h1'].append(short_name)
            
        # Img Alt
        imgs = soup.find_all('img')
        for img in imgs:
            if not img.get('alt'):
                if short_name not in report['missing_alt']:
                    report['missing_alt'].append(short_name)
                break
                
        # Links
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            if href and href.startswith('/'):
                # Ignore query params or hash
                base_href = href.split('?')[0].split('#')[0]
                if base_href and base_href not in valid_paths and base_href not in ['/blog', '/case-studies', '/api/v1', '/api', '/llms-full.txt']:
                    if not (os.path.exists(os.path.join(STATIC_DIR, base_href.lstrip('/'))) or \
                            os.path.exists(os.path.join(STATIC_DIR, base_href.lstrip('/') + '.html'))):
                        report['broken_links'][short_name].append(href)

    # Print Report
    print("==================================================")
    print(f"       WEBSITE HEALTH REPORT ({report['total_pages']} static pages)")
    print("==================================================")
    
    def print_section(title, data, is_dict=False):
        print(f"\n[ {title} ]")
        if not data:
            print("  ✅ All good! None found.")
            return
            
        if is_dict:
            for page, issues in data.items():
                print(f"  ❌ {page}:")
                for issue in list(set(issues)):
                    print(f"     -> {issue}")
        else:
            for page in data:
                print(f"  ❌ {page}")

    print_section("Pages Missing Title", report['missing_title'])
    print_section("Pages Missing Meta Description", report['missing_desc'])
    print_section("Pages Missing Canonical Tag", report['missing_canonical'])
    print_section("Pages Missing <h1> Tag", report['missing_h1'])
    print_section("Pages with Multiple <h1> Tags", report['multiple_h1'])
    print_section("Pages with Images Missing Alt Attributes", report['missing_alt'])
    print_section("Potentially Broken Internal Links", report['broken_links'], is_dict=True)
    print("\n==================================================")
    print("Report complete. This output relies strictly on local static tracking.")

if __name__ == '__main__':
    generate_report()
