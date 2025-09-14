"""
Unit tests for TikTok HTML Parser
"""
from app.services.tiktok.parser.utils import parse_like_count
from app.services.tiktok.parser.html_parser import extract_video_data_from_html
from pathlib import Path


class TestTikTokParser:
    """Unit tests for TikTok HTML parsing functionality"""

    def test_parse_like_count_with_k_suffix(self):
        """Test parsing like count with K suffix"""
        assert parse_like_count("15.9K") == 15900
        assert parse_like_count("1K") == 1000
        assert parse_like_count("0.5K") == 500

    def test_parse_like_count_with_m_suffix(self):
        """Test parsing like count with M suffix"""
        assert parse_like_count("1.2M") == 1200000
        assert parse_like_count("2M") == 2000000
        assert parse_like_count("0.5M") == 500000

    def test_parse_like_count_with_integer(self):
        """Test parsing like count with integer value"""
        assert parse_like_count("12345") == 12345
        assert parse_like_count("0") == 0
        assert parse_like_count("100") == 100

    def test_parse_like_count_with_invalid_input(self):
        """Test parsing like count with invalid input"""
        assert parse_like_count("") == 0
        assert parse_like_count(None) == 0
        assert parse_like_count("invalid") == 0
        assert parse_like_count("abcK") == 0

    def test_extract_video_data_from_html_with_valid_html(self):
        """Test extracting video data from valid HTML"""
        html_content = '''
        <div id="column-item-video-container-1">
            <a href="https://www.tiktok.com/@testuser/video/123456789">Video Link</a>
            <div class="search-card-video-caption">Test video caption</div>
            <span class="css-1i43xsj">15.9K</span>
            <div>2023-01-01</div>
        </div>
        '''

        results = extract_video_data_from_html(html_content)

        assert len(results) == 1
        video = results[0]
        assert video["id"] == "123456789"
        assert video["caption"] == "Test video caption"
        assert video["authorHandle"] == "testuser"
        assert video["likeCount"] == 15900
        assert video["uploadTime"] == "2023-01-01"
        assert video["webViewUrl"] == "https://www.tiktok.com/@testuser/video/123456789"

    def test_extract_video_data_from_html_with_multiple_videos(self):
        """Test extracting video data from HTML with multiple videos"""
        html_content = '''
        <div id="column-item-video-container-1">
            <a href="https://www.tiktok.com/@user1/video/11111111">Video 1</a>
            <div class="search-card-video-caption">Caption 1</div>
            <span class="css-1i43xsj">10K</span>
            <div>2023-01-01</div>
        </div>
        <div id="column-item-video-container-2">
            <a href="https://www.tiktok.com/@user2/video/22222222">Video 2</a>
            <div class="search-card-video-caption">Caption 2</div>
            <span class="css-1i43xsj">20K</span>
            <div>2023-01-02</div>
        </div>
        '''

        results = extract_video_data_from_html(html_content)

        assert len(results) == 2
        assert results[0]["id"] == "11111111"
        assert results[0]["uploadTime"] == "2023-01-01"
        assert results[1]["id"] == "22222222"
        assert results[1]["uploadTime"] == "2023-01-02"

    def test_extract_video_data_from_html_with_missing_data(self):
        """Test extracting video data from HTML with missing data"""
        html_content = '''
        <div id="column-item-video-container-1">
            <a href="https://www.tiktok.com/@testuser/video/123456789">Video Link</a>
        </div>
        '''

        results = extract_video_data_from_html(html_content)

        assert len(results) == 1
        video = results[0]
        assert video["id"] == "123456789"
        assert video["webViewUrl"] == "https://www.tiktok.com/@testuser/video/123456789"
        # Other fields should have default values
        assert video["caption"] == "Video Link"
        assert video["authorHandle"] == "testuser"
        assert video["likeCount"] == 0
        assert video["uploadTime"] == ""  # Still empty as no time element is present

    def test_extract_video_data_from_html_with_empty_html(self):
        """Test extracting video data from empty HTML"""
        results = extract_video_data_from_html("")
        assert len(results) == 0

    def test_extract_video_data_from_html_with_no_matching_containers(self):
        """Test extracting video data from HTML with no matching containers"""
        html_content = '''
        <div class="other-container">
            <a href="https://www.tiktok.com/@testuser/video/123456789">Video Link</a>
        </div>
        '''

        results = extract_video_data_from_html(html_content)
        assert len(results) == 0

    def test_extract_video_data_from_demo_html(self):
        """Test extracting video data from a mock demo HTML file"""
        mock_path = Path(__file__).parent / "mock_browsing_tiktok_search.html"
        with open(mock_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        results = extract_video_data_from_html(html_content)

        # Assert that results are not empty
        assert len(results) > 0

        # Find a specific video by ID and check its uploadTime
        # Using a video from the mock HTML: 7474929793650216214 (first one in the HTML)
        found_video = next((video for video in results if video["id"] == "7474929793650216214"), None)
        assert found_video is not None, "Video with ID 7474929793650216214 not found"
        assert found_video["uploadTime"] == "2-24"   # Expected upload time from the mock HTML

        # Another video: 7343616838871338260 (second one in the mock HTML)
        found_video = next((video for video in results if video["id"] == "7343616838871338260"), None)
        assert found_video is not None, "Video with ID 7343616838871338260 not found"
        assert found_video["uploadTime"] == "2024-3-7"   # Expected upload time from the mock HTML
