#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script cho việc sử dụng matching rules để ánh xạ từ khóa tiếng Việt 
sang các class và property trong ontology
"""

import json
import re
from typing import Dict, List, Tuple, Optional

class MatchingRuleEngine:
    def __init__(self, rules_file: str = "matching_rules.json"):
        """Khởi tạo engine với file rules"""
        with open(rules_file, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
        
        # Tạo index ngược từ keyword -> class/property
        self.keyword_to_class = {}
        self.keyword_to_property = {}
        
        for class_name, class_info in self.rules["classes"].items():
            for keyword in class_info["keywords"]:
                self.keyword_to_class[keyword.lower()] = class_name
        
        for prop_name, prop_info in self.rules["properties"].items():
            for keyword in prop_info["keywords"]:
                self.keyword_to_property[keyword.lower()] = prop_name
    
    def find_classes_in_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Tìm các class trong text
        Returns: List of (keyword, class_name) tuples
        """
        found_classes = []
        text_lower = text.lower()
        
        for keyword, class_name in self.keyword_to_class.items():
            if keyword in text_lower:
                found_classes.append((keyword, class_name))
        
        return found_classes
    
    def find_properties_in_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Tìm các property trong text
        Returns: List of (keyword, property_name) tuples
        """
        found_properties = []
        text_lower = text.lower()
        
        for keyword, prop_name in self.keyword_to_property.items():
            if keyword in text_lower:
                found_properties.append((keyword, prop_name))
        
        return found_properties
    
    def extract_triples(self, text: str) -> List[Dict]:
        """
        Trích xuất các triple (Subject, Predicate, Object) từ text
        """
        classes = self.find_classes_in_text(text)
        properties = self.find_properties_in_text(text)
        
        triples = []
        
        # Tạo các triple từ các class và property tìm được
        for class_keyword, class_name in classes:
            for prop_keyword, prop_name in properties:
                # Tìm vị trí của keyword trong text
                class_pos = text.lower().find(class_keyword)
                prop_pos = text.lower().find(prop_keyword)
                
                if class_pos != -1 and prop_pos != -1:
                    # Xác định subject, predicate, object dựa trên vị trí
                    if class_pos < prop_pos:
                        # Class trước property -> Subject là class
                        subject = self.extract_entity_around_position(text, class_pos, class_keyword)
                        predicate = prop_name
                        object_entity = self.extract_entity_around_position(text, prop_pos, prop_keyword)
                    else:
                        # Property trước class -> Subject là entity xung quanh property
                        subject = self.extract_entity_around_position(text, prop_pos, prop_keyword)
                        predicate = prop_name
                        object_entity = self.extract_entity_around_position(text, class_pos, class_keyword)
                    
                    triple = {
                        "subject": subject,
                        "predicate": predicate,
                        "object": object_entity,
                        "subject_type": class_name,
                        "confidence": self.calculate_confidence(class_keyword, prop_keyword)
                    }
                    triples.append(triple)
        
        return triples
    
    def extract_entity_around_position(self, text: str, pos: int, keyword: str) -> str:
        """
        Trích xuất entity xung quanh vị trí keyword
        """
        # Lấy context xung quanh keyword (50 ký tự trước và sau)
        start = max(0, pos - 50)
        end = min(len(text), pos + len(keyword) + 50)
        context = text[start:end]
        
        # Tìm tên riêng trong context (có thể cải thiện bằng NER)
        words = context.split()
        entities = []
        
        for word in words:
            # Lọc các từ có thể là tên riêng (chữ cái đầu viết hoa, dài > 2)
            if len(word) > 2 and word[0].isupper():
                entities.append(word)
        
        return " ".join(entities) if entities else context.strip()
    
    def calculate_confidence(self, class_keyword: str, prop_keyword: str) -> float:
        """
        Tính độ tin cậy của match
        """
        # Độ tin cậy dựa trên độ dài và độ cụ thể của keyword
        class_score = len(class_keyword) / 20.0  # Normalize
        prop_score = len(prop_keyword) / 20.0
        
        return min(1.0, (class_score + prop_score) / 2.0)
    
    def get_all_keywords(self) -> Dict[str, List[str]]:
        """Lấy tất cả keywords cho việc lọc text"""
        all_keywords = []
        
        for class_info in self.rules["classes"].values():
            all_keywords.extend(class_info["keywords"])
        
        for prop_info in self.rules["properties"].values():
            all_keywords.extend(prop_info["keywords"])
        
        return {
            "classes": list(self.rules["classes"].keys()),
            "properties": list(self.rules["properties"].keys()),
            "all_keywords": all_keywords
        }

def demo_usage():
    """Demo cách sử dụng MatchingRuleEngine"""
    
    # Khởi tạo engine
    engine = MatchingRuleEngine()
    
    # Ví dụ text từ Wikipedia
    sample_texts = [
        "Nguyễn Quang Hải là cầu thủ bóng đá chuyên nghiệp thi đấu cho đội tuyển Việt Nam.",
        "Trận đấu giữa Manchester United và Liverpool diễn ra tại sân vận động Old Trafford.",
        "Lionel Messi có quốc tịch Argentina và thi đấu ở vị trí tiền đạo.",
        "Câu lạc bộ Barcelona được thành lập vào ngày 29 tháng 11 năm 1899.",
        "Cristiano Ronaldo ghi bàn thắng ở phút thứ 67 trong trận đấu.",
        "Huấn luyện viên trưởng của đội tuyển Việt Nam là ông Park Hang-seo."
    ]
    
    print("=== DEMO MATCHING RULES ENGINE ===\n")
    
    for i, text in enumerate(sample_texts, 1):
        print(f"Text {i}: {text}")
        
        # Tìm classes
        classes = engine.find_classes_in_text(text)
        print(f"Classes tìm được: {classes}")
        
        # Tìm properties  
        properties = engine.find_properties_in_text(text)
        print(f"Properties tìm được: {properties}")
        
        # Trích xuất triples
        triples = engine.extract_triples(text)
        print(f"Triples: {triples}")
        
        print("-" * 80)
    
    # Hiển thị thống kê
    stats = engine.get_all_keywords()
    print(f"\n=== THỐNG KÊ ===")
    print(f"Tổng số classes: {len(stats['classes'])}")
    print(f"Tổng số properties: {len(stats['properties'])}")
    print(f"Tổng số keywords: {len(stats['all_keywords'])}")

if __name__ == "__main__":
    demo_usage()
