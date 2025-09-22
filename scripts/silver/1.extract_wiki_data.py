#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để trích xuất dữ liệu từ các file JSON Wikipedia
Trích xuất: title, content (revision cuối cùng), touched, canonicalurl
"""

import json
import os
import glob
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from tqdm import tqdm

class WikiDataExtractor:
    def __init__(self, input_dir: str = "bronze/wiki_raw"):
        """
        Khởi tạo extractor
        
        Args:
            input_dir: Thư mục chứa các file JSON Wikipedia
        """
        self.input_dir = Path(input_dir)
        
    def extract_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Trích xuất dữ liệu từ một file JSON
        
        Args:
            file_path: Đường dẫn đến file JSON
            
        Returns:
            Dict chứa title, content, touched, canonicalurl hoặc None nếu lỗi
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Kiểm tra cấu trúc dữ liệu
            if 'query' not in data or 'pages' not in data['query']:
                print(f"File {file_path} không có cấu trúc hợp lệ")
                return None
            
            pages = data['query']['pages']
            
            # Xử lý trường hợp pages là list hoặc dict
            if isinstance(pages, list):
                if not pages:
                    print(f"File {file_path} có pages rỗng")
                    return None
                page = pages[0]  # Lấy page đầu tiên
            elif isinstance(pages, dict):
                if not pages:
                    print(f"File {file_path} không có pages")
                    return None
                page = list(pages.values())[0]  # Lấy page đầu tiên
            else:
                print(f"File {file_path} có cấu trúc pages không hợp lệ")
                return None
            
            result = {
                'title': page.get('title', ''),
                'content': '',
                'touched': page.get('touched', ''),
                'canonicalurl': page.get('canonicalurl', ''),
                'pageid': page.get('pageid', '')
            }
            
            # Kiểm tra nếu page bị missing
            if page.get('missing', False):
                return result
            
            # Lấy content từ revision cuối cùng
            if 'revisions' in page and page['revisions']:
                revisions = page['revisions']
                if revisions:
                    last_revision = revisions[-1]  # Revision cuối cùng
                    if 'slots' in last_revision and 'main' in last_revision['slots']:
                        result['content'] = last_revision['slots']['main'].get('content', '')
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Lỗi JSON trong file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Lỗi khi đọc file {file_path}: {e}")
            return None
    
    def extract_from_directory(self, pattern: str = "*.json") -> List[Dict]:
        """
        Trích xuất dữ liệu từ tất cả file JSON trong thư mục
        
        Args:
            pattern: Pattern để tìm file (mặc định: *.json)
            
        Returns:
            List các Dict chứa dữ liệu trích xuất
        """
        if not self.input_dir.exists():
            print(f"Thư mục {self.input_dir} không tồn tại")
            return []
        
        # Tìm tất cả file JSON
        json_files = list(self.input_dir.glob(pattern))
        print(f"Tìm thấy {len(json_files)} file JSON trong {self.input_dir}")
        
        results = []
        for file_path in tqdm(json_files, desc="Đang xử lý"):
            data = self.extract_from_file(str(file_path))
            if data:
                results.append(data)
        
        return results
    
    def save_to_json(self, data: List[Dict], output_file: str = "silver/extracted_wiki/extracted_wiki_data.json"):
        """
        Lưu dữ liệu đã trích xuất vào file JSON
        
        Args:
            data: List dữ liệu đã trích xuất
            output_file: Tên file output
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu {len(data)} records vào {output_file}")
        except Exception as e:
            print(f"Lỗi khi lưu file {output_file}: {e}")
    
    def print_summary(self, data: List[Dict]):
        """
        In tóm tắt dữ liệu đã trích xuất
        
        Args:
            data: List dữ liệu đã trích xuất
        """
        if not data:
            print("Không có dữ liệu để hiển thị")
            return
        
        print(f"\n=== TÓM TẮT DỮ LIỆU ===")
        print(f"Tổng số file đã xử lý: {len(data)}")
        
        # Thống kê về content
        with_content = [d for d in data if d['content']]
        print(f"File có content: {len(with_content)}")
        
        # Thống kê về độ dài content
        if with_content:
            lengths = [len(d['content']) for d in with_content]
            print(f"Độ dài content trung bình: {sum(lengths)/len(lengths):.0f} ký tự")
            print(f"Độ dài content min: {min(lengths)} ký tự")
            print(f"Độ dài content max: {max(lengths)} ký tự")
        
        # Hiển thị một vài ví dụ
        print(f"\n=== VÍ DỤ DỮ LIỆU ===")
        for i, item in enumerate(data[:3]):  # Hiển thị 3 item đầu
            print(f"\n{i+1}. Title: {item['title']}")
            print(f"   Content length: {len(item['content'])} ký tự")
            print(f"   Touched: {item['touched']}")
            print(f"   URL: {item['canonicalurl']}")
            if item['content']:
                # Hiển thị 100 ký tự đầu của content
                preview = item['content'][:100].replace('\n', ' ')
                print(f"   Content preview: {preview}...")

def main():
    """Hàm main để chạy script"""
    # Khởi tạo extractor
    extractor = WikiDataExtractor("bronze/wiki_raw")
    
    # Trích xuất dữ liệu từ tất cả file JSON
    print("Bắt đầu trích xuất dữ liệu...")
    data = extractor.extract_from_directory("*.json")
    
    if data:
        # In tóm tắt
        extractor.print_summary(data)
        
        # Lưu vào file JSON
        extractor.save_to_json(data, "silver/extracted_wiki/extracted_wiki_data.json")
        
        print(f"\nHoàn thành! Đã trích xuất {len(data)} file.")
    else:
        print("Không tìm thấy dữ liệu nào để trích xuất.")

if __name__ == "__main__":
    main()
