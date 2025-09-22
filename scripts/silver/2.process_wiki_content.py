#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xử lý content từ file extracted_wiki_data.json
- Lọc câu có link/ảnh hoặc từ khóa trong matching_rules
- NER để phân ra S, P, O
- Match với class/property trong ontology
"""

import json
import re
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from tqdm import tqdm

class WikiContentProcessor:
    def __init__(self, extracted_file: str = "silver/extracted_wiki/extracted_wiki_data.json", 
                 rules_file: str = "scripts/silver/matching_rules.json"):
        """
        Khởi tạo processor
        
        Args:
            extracted_file: File chứa dữ liệu đã trích xuất
            rules_file: File chứa matching rules
        """
        self.extracted_file = Path(extracted_file)
        self.rules_file = Path(rules_file)
        self.matching_rules = self._load_matching_rules()
        self.all_keywords = self._get_all_keywords()
        
    def _load_matching_rules(self) -> Dict:
        """Load matching rules từ file JSON"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi khi load matching rules: {e}")
            return {"classes": {}, "properties": {}}
    
    def _get_all_keywords(self) -> Set[str]:
        """Lấy tất cả keywords để tìm kiếm nhanh"""
        keywords = set()
        
        for class_info in self.matching_rules.get("classes", {}).values():
            keywords.update(class_info.get("keywords", []))
        
        for prop_info in self.matching_rules.get("properties", {}).values():
            keywords.update(prop_info.get("keywords", []))
        
        return keywords
    
    def _has_links_or_images(self, text: str) -> bool:
        """Kiểm tra xem text có chứa link hoặc ảnh không"""
        # Pattern cho link Wikipedia [[...]]
        wiki_link_pattern = r'\[\[([^\]]+)\]\]'
        # Pattern cho ảnh [[File:...]] hoặc [[Tập tin:...]]
        image_pattern = r'\[\[(?:File|Tập tin):[^\]]+\]\]'
        # Pattern cho external link [url text]
        external_link_pattern = r'\[[^\]]+\]'
        
        return bool(re.search(wiki_link_pattern, text) or 
                   re.search(image_pattern, text) or 
                   re.search(external_link_pattern, text))
    
    def _has_matching_keywords(self, text: str) -> bool:
        """Kiểm tra xem text có chứa từ khóa nào trong matching rules không"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.all_keywords)
    
    def _parse_wiki_content(self, content: str) -> List[str]:
        """Xử lý wiki text và trích xuất các câu có ý nghĩa"""
        # Xử lý các bảng biểu - trích xuất thông tin từ bảng
        table_sentences = self._extract_table_info(content)
        
        # Xử lý infobox - trích xuất thông tin từ infobox
        infobox_sentences = self._extract_infobox_info(content)
        
        # Xử lý links - chuyển đổi links thành text có ý nghĩa
        content = self._process_links(content)
        
        # Loại bỏ các template và markup phức tạp
        content = re.sub(r'\{\{[^}]*\}\}', '', content)  # Loại bỏ templates
        content = re.sub(r'<ref[^>]*>.*?</ref>', '', content, flags=re.DOTALL)  # Loại bỏ references
        content = re.sub(r'<[^>]+>', '', content)  # Loại bỏ HTML tags
        
        # Chia thành câu dựa trên dấu chấm, chấm hỏi, chấm than
        sentences = re.split(r'[.!?]+', content)
        
        # Lọc và làm sạch câu
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Chỉ lấy câu có độ dài > 10 ký tự
                clean_sentences.append(sentence)
        
        # Kết hợp tất cả các câu
        all_sentences = table_sentences + infobox_sentences + clean_sentences
        return all_sentences
    
    def _extract_table_info(self, content: str) -> List[str]:
        """Trích xuất thông tin từ bảng biểu"""
        sentences = []
        
        # Tìm các bảng {| ... |}
        table_pattern = r'\{\|.*?\|\}'
        tables = re.findall(table_pattern, content, re.DOTALL)
        
        for table in tables:
            # Tìm tiêu đề bảng (sau |+)
            title_match = re.search(r'\|\+\s*([^\n]+)', table)
            table_title = ""
            if title_match:
                table_title = title_match.group(1).strip()
                if len(table_title) > 10:
                    sentences.append(table_title)
            
            # Trích xuất các hàng dữ liệu có ý nghĩa
            lines = table.split('\n')
            current_row_data = []
            
            for line in lines:
                line = line.strip()
                
                # Bỏ qua các dòng không quan trọng
                if (not line or 
                    line.startswith('{|') or 
                    line.startswith('|}') or 
                    line.startswith('|-') or
                    line.startswith('!') or
                    line.startswith('|+') or
                    len(line) < 5):
                    continue
                
                # Xử lý dòng có dữ liệu
                if line.startswith('|'):
                    # Loại bỏ ký tự | đầu và tách các ô
                    data = line[1:].strip()
                    cells = [cell.strip() for cell in data.split('|')]
                    
                    # Lọc các ô có ý nghĩa (không phải số thuần túy, không rỗng)
                    meaningful_cells = []
                    for cell in cells:
                        cell = cell.strip()
                        if (len(cell) > 3 and 
                            not cell.isdigit() and 
                            not re.match(r'^\d+$', cell) and
                            cell not in ['—', '-', 'N/A', '']):
                            meaningful_cells.append(cell)
                    
                    # Nếu có ít nhất 2 ô có ý nghĩa, tạo câu mô tả
                    if len(meaningful_cells) >= 2:
                        if len(meaningful_cells) == 2:
                            # Dạng: "A là B"
                            sentence = f"{meaningful_cells[0]} là {meaningful_cells[1]}"
                        else:
                            # Dạng: "A là B trong C"
                            sentence = f"{meaningful_cells[0]} là {meaningful_cells[1]} trong {meaningful_cells[2]}"
                        
                        if len(sentence) > 15:
                            sentences.append(sentence)
                    elif len(meaningful_cells) == 1 and len(meaningful_cells[0]) > 10:
                        # Chỉ có 1 ô có ý nghĩa và đủ dài
                        sentences.append(meaningful_cells[0])
        
        return sentences
    
    def _extract_infobox_info(self, content: str) -> List[str]:
        """Trích xuất thông tin từ infobox"""
        sentences = []
        
        # Tìm infobox {{Infobox ...}}
        infobox_pattern = r'\{\{Infobox[^}]*\}\}'
        infoboxes = re.findall(infobox_pattern, content, re.DOTALL)
        
        for infobox in infoboxes:
            # Trích xuất các trường trong infobox
            lines = infobox.split('\n')
            for line in lines:
                line = line.strip()
                
                # Tìm dòng có format |field = value
                if '|' in line and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        field = parts[0].replace('|', '').strip()
                        value = parts[1].strip()
                        
                        # Làm sạch field và value
                        field = re.sub(r'[{}]', '', field)
                        value = re.sub(r'[{}]', '', value)
                        
                        # Loại bỏ các template phức tạp trong value
                        value = re.sub(r'\{\{[^}]*\}\}', '', value)
                        value = re.sub(r'<ref[^>]*>.*?</ref>', '', value, flags=re.DOTALL)
                        value = re.sub(r'\[\[([^\]]+)\]\]', r'\1', value)  # Chuyển [[text]] thành text
                        value = value.strip()
                        
                        if len(field) > 2 and len(value) > 3:
                            # Tạo câu có ý nghĩa
                            sentence = f"{field} là {value}"
                            if len(sentence) > 10:
                                sentences.append(sentence)
        
        return sentences
    
    def _process_links(self, content: str) -> str:
        """Xử lý links Wikipedia thành text có ý nghĩa"""
        # Xử lý links dạng [[text|display]] hoặc [[text]]
        def replace_link(match):
            link_content = match.group(1)
            if '|' in link_content:
                # [[text|display]] -> display
                return link_content.split('|')[-1]
            else:
                # [[text]] -> text
                return link_content
        
        content = re.sub(r'\[\[([^\]]+)\]\]', replace_link, content)
        
        # Xử lý external links [url text] -> text
        content = re.sub(r'\[[^\s]+\s+([^\]]+)\]', r'\1', content)
        
        return content
    
    
    def process_sentence(self, sentence: str) -> Optional[str]:
        """Xử lý một câu và trả về câu đã lọc"""
        # Kiểm tra xem câu có đáng giữ lại không
        has_links = self._has_links_or_images(sentence)
        has_keywords = self._has_matching_keywords(sentence)
        
        # Chỉ giữ lại câu có từ khóa hoặc có hình ảnh/link
        if has_links or has_keywords:
            return sentence.strip()
        
        return None
    
    def process_content(self, content: str) -> List[str]:
        """Xử lý toàn bộ content"""
        sentences = self._parse_wiki_content(content)
        processed_sentences = []
        
        for sentence in sentences:
            result = self.process_sentence(sentence)
            if result:
                processed_sentences.append(result)
        
        return processed_sentences
    
    def process_file(self, limit: Optional[int] = None) -> List[Dict]:
        """Xử lý toàn bộ file extracted"""
        try:
            with open(self.extracted_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Lỗi khi đọc file {self.extracted_file}: {e}")
            return []
        
        # Giới hạn số lượng items nếu cần
        if limit:
            data = data[:limit]
        
        results = []
        for item in tqdm(data, desc="Đang xử lý"):
            if not item.get('content'):
                continue
            
            processed_content = self.process_content(item['content'])
            if processed_content:
                results.append({
                    "title": item['title'],
                    "pageid": item.get('pageid', ''),
                    "canonicalurl": item.get('canonicalurl', ''),
                    "filtered_sentences": processed_content
                })
        
        return results
    
    def save_results(self, results: List[Dict], output_file: str = "silver/processed_wiki/processed_content.json"):
        """Lưu kết quả xử lý"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu {len(results)} items vào {output_file}")
        except Exception as e:
            print(f"Lỗi khi lưu file {output_file}: {e}")
    
    def print_summary(self, results: List[Dict]):
        """In tóm tắt kết quả"""
        if not results:
            print("Không có dữ liệu để hiển thị")
            return
        
        total_sentences = sum(len(item['filtered_sentences']) for item in results)
        
        print(f"\n=== TÓM TẮT XỬ LÝ ===")
        print(f"Tổng số items: {len(results)}")
        print(f"Tổng số câu đã lọc: {total_sentences}")
        
        # Hiển thị ví dụ
        print(f"\n=== VÍ DỤ XỬ LÝ ===")
        for i, item in enumerate(results[:2]):  # Hiển thị 2 items đầu
            print(f"\n{i+1}. Title: {item['title']}")
            print(f"   Số câu đã lọc: {len(item['filtered_sentences'])}")
            
            for j, sentence in enumerate(item['filtered_sentences'][:3]):  # Hiển thị 3 câu đầu
                print(f"   Câu {j+1}: {sentence[:100]}{'...' if len(sentence) > 100 else ''}")

def main():
    """Hàm main để chạy script"""
    processor = WikiContentProcessor()
    
    print("Bắt đầu xử lý content...")
    
    # Test với 5 items đầu
    print("\n=== TEST VỚI 5 ITEMS ĐẦU ===")
    test_results = processor.process_file(limit=10)
    processor.print_summary(test_results)
    processor.save_results(test_results, "silver/processed_wiki/test_processed_content.json")
    
    # # Xử lý toàn bộ file
    # print("\n=== XỬ LÝ TOÀN BỘ FILE ===")
    # all_results = processor.process_file()
    # processor.print_summary(all_results)
    # processor.save_results(all_results, "silver/processed_wiki/processed_content.json")
    
    # print(f"\nHoàn thành! Đã xử lý {len(all_results)} items.")

if __name__ == "__main__":
    main()
