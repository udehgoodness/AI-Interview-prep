"""
Text Processing Utilities
----------------------
This module contains utility functions for text processing.
"""

def is_likely_gibberish(text, is_voice_mode=False):
    """
    Check if text is likely gibberish or nonsensical.
    
    Args:
        text (str): The text to check
        is_voice_mode (bool): Whether the text is from voice mode (more lenient checking)
        
    Returns:
        bool: True if the text is likely gibberish, False otherwise
    """
    if not text or text.strip() == "":
        return True
        
    # For voice mode, be more lenient
    if is_voice_mode:
        # Only check for empty or very short answers
        if len(text.strip()) < 5:
            return True
        return False
        
    # Check for random character sequences
    if len(text) < 10:
        return True
        
    # Check for keyboard smashing patterns
    keyboard_rows = [
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm"
    ]
    
    # Convert to lowercase for comparison
    lower_text = text.lower()
    
    # Check for repeated characters
    for char in "abcdefghijklmnopqrstuvwxyz":
        if char * 3 in lower_text:
            return True
            
    # Check for keyboard row patterns
    for row in keyboard_rows:
        for i in range(len(row) - 2):
            if row[i:i+3] in lower_text:
                return True
                
    # Check for lack of spaces (indicating no real words)
    if " " not in text and len(text) > 15:
        return True
        
    # Check for random character distribution
    char_counts = {}
    for char in lower_text:
        if char.isalpha():
            char_counts[char] = char_counts.get(char, 0) + 1
            
    # If very few unique characters are used repeatedly, likely gibberish
    if len(char_counts) < 5 and len(text) > 10:
        return True
        
    return False 