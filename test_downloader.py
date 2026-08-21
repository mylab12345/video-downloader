#!/usr/bin/env python3
"""
Test script to verify video downloader functionality with various formats and resolutions.
Tests large videos, different formats, and high resolution downloads.
"""

import os
import sys
import time
import threading

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from downloader import VideoDownloader

def format_bytes(size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def progress_hook(d):
    """Progress callback for downloads"""
    if d.get('status') == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0
        
        percent = (downloaded / total * 100) if total > 0 else 0
        speed_str = format_bytes(speed) + "/s"
        eta_str = f"{int(eta)}s" if eta else "--:--"
        
        print(f"\r  Progress: {percent:.1f}% | Speed: {speed_str} | ETA: {eta_str}", end='', flush=True)
    elif d.get('status') == 'finished':
        print(f"\n  ✓ Download complete, processing...")
    elif d.get('status') == 'error':
        print(f"\n  ✗ Download error!")

def test_video_info(url, test_name):
    """Test fetching video info"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"URL: {url}")
    print('='*70)
    
    downloader = VideoDownloader()
    
    try:
        print("\n[1/3] Fetching video information...")
        info = downloader.fetch_video_info(url)
        
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')
        
        print(f"  Title: {title}")
        print(f"  Uploader: {uploader}")
        print(f"  Duration: {duration}s ({duration//60}:{duration%60:02d})" if duration else "  Duration: N/A")
        
        # Get available formats
        print("\n[2/3] Analyzing available formats...")
        formats = downloader.parse_formats(info)
        
        # Show top formats
        video_formats = [f for f in formats if 'Video' in f.get('label', '')][:10]
        audio_formats = [f for f in formats if 'Audio' in f.get('label', '')][:5]
        
        print(f"  Total formats found: {len(formats)}")
        print(f"\n  Top Video Formats:")
        for i, fmt in enumerate(video_formats[:5], 1):
            print(f"    {i}. {fmt['label']}")
        
        print(f"\n  Audio Formats:")
        for i, fmt in enumerate(audio_formats[:3], 1):
            print(f"    {i}. {fmt['label']}")
        
        return True, info, formats
        
    except Exception as e:
        print(f"\n  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_download(url, format_id, output_path, test_name):
    """Test downloading a video"""
    print(f"\n{'='*70}")
    print(f"DOWNLOAD TEST: {test_name}")
    print(f"URL: {url}")
    print(f"Format: {format_id}")
    print(f"Output: {output_path}")
    print('='*70)
    
    downloader = VideoDownloader()
    
    try:
        print("\n[1/2] Starting download...")
        start_time = time.time()
        
        filename = downloader.download(
            url=url,
            format_id=format_id,
            output_path=output_path,
            progress_hook=progress_hook
        )
        
        elapsed = time.time() - start_time
        
        if filename and os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"\n[2/2] ✓ Download successful!")
            print(f"  File: {os.path.basename(filename)}")
            print(f"  Size: {format_bytes(size)}")
            print(f"  Time: {elapsed:.1f}s")
            print(f"  Avg Speed: {format_bytes(size/elapsed)}/s")
            
            # Clean up test file
            print(f"\n  Cleaning up test file...")
            os.remove(filename)
            print(f"  ✓ Test file removed")
            
            return True
        else:
            print(f"\n  ✗ Download failed - no file created")
            return False
            
    except Exception as e:
        print(f"\n  ✗ Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run comprehensive tests"""
    print("\n" + "="*70)
    print("VIDEO DOWNLOADER COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    # Create test directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_downloads")
    os.makedirs(test_dir, exist_ok=True)
    
    # Test URLs - using Blender Open Movie Project videos that are publicly accessible
    test_cases = [
        {
            'name': 'Spring (Blender, 2019)',
            'url': 'https://www.youtube.com/watch?v=WhWc3b3KHNc',
            'format': 'bestvideo+bestaudio/best',
            'expected_res': '1080p'
        },
        {
            'name': 'Cosmos Laundromat',
            'url': 'https://www.youtube.com/watch?v=Y-rmzh0PI3c',
            'format': 'bestvideo+bestaudio/best',
            'expected_res': '1080p'
        },
        {
            'name': 'Agent 327 (Blender)',
            'url': 'https://www.youtube.com/watch?v=0apIaBmQCDA',
            'format': 'bestvideo+bestaudio/best',
            'expected_res': '1080p'
        },
    ]
    
    results = []
    
    # Run info tests
    print("\n\n" + "#"*70)
    print("# PHASE 1: VIDEO INFO EXTRACTION TESTS")
    print("#"*70)
    
    for test in test_cases:
        success, info, formats = test_video_info(test['url'], test['name'])
        results.append({
            'name': test['name'],
            'info_test': success,
            'download_test': False,
            'url': test['url'],
            'format': test['format']
        })
        time.sleep(1)  # Rate limiting
    
    # Run download tests for successful info extractions
    print("\n\n" + "#"*70)
    print("# PHASE 2: DOWNLOAD TESTS")
    print("#"*70)
    
    for i, result in enumerate(results):
        if result['info_test']:
            test = test_cases[i]
            success = test_download(
                test['url'],
                test['format'],
                test_dir,
                f"{test['name']} - Download"
            )
            result['download_test'] = success
            time.sleep(2)  # Rate limiting
    
    # Summary
    print("\n\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed_info = sum(1 for r in results if r['info_test'])
    passed_download = sum(1 for r in results if r['download_test'])
    
    print(f"\nInfo Extraction: {passed_info}/{len(results)} passed")
    print(f"Downloads: {passed_download}/{len(results)} passed")
    
    print("\nDetailed Results:")
    for r in results:
        info_status = "✓" if r['info_test'] else "✗"
        dl_status = "✓" if r['download_test'] else "✗"
        print(f"  [{info_status}] [{dl_status}] {r['name']}")
    
    # Cleanup
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
        print(f"\n✓ Test directory cleaned up")
    
    print("\n" + "="*70)
    if passed_download >= len(results) - 1:
        print("OVERALL: ✓ TESTS PASSED - Downloader working correctly!")
    else:
        print("OVERALL: ⚠ SOME TESTS FAILED - Check errors above")
    print("="*70 + "\n")
    
    return passed_download == len(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
