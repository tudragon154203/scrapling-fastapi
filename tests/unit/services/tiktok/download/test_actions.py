"""Unit tests for TikTok download actions."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.tiktok.download.actions.resolver import TikVidResolveAction


class TestTikVidResolveAction:
    """Test cases for TikVidResolveAction."""

    @pytest.fixture
    def action(self):
        """Create a TikVidResolveAction instance."""
        return TikVidResolveAction(
            tiktok_url="https://www.tiktok.com/@username/video/1234567890",
            quality_hint="HD"
        )

    def test_action_initialization(self):
        """Test action initialization."""
        url = "https://www.tiktok.com/@test/video/9876543210"
        quality = "SD"
        action = TikVidResolveAction(url, quality)

        assert action.tiktok_url == url
        assert action.quality_hint == quality.lower().strip() or quality
        assert action.result_links == []

    def test_action_initialization_without_quality(self):
        """Test action initialization without quality hint."""
        url = "https://www.tiktok.com/@test/video/9876543210"
        action = TikVidResolveAction(url)

        assert action.tiktok_url == url
        assert action.quality_hint is None

    def test_action_initialization_quality_normalization(self):
        """Test quality hint normalization during initialization."""
        action = TikVidResolveAction(
            "https://www.tiktok.com/@test/video/123",
            quality_hint="  hd  "  # With whitespace and mixed case
        )

        assert action.quality_hint == "hd"

    def test_action_call(self):
        """Test action call method."""
        url = "https://www.tiktok.com/@test/video/9876543210"
        action = TikVidResolveAction(url)
        mock_page = Mock()
        action._execute = Mock(return_value=mock_page)

        result = action(mock_page)

        assert result == mock_page
        action._execute.assert_called_once_with(mock_page)

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_navigation_needed(self, action):
        """Test execution when navigation to TikVid is needed."""
        mock_page = Mock()
        mock_page.url = "https://other-site.com"
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()

        # Mock all the interaction methods
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))
        mock_page.keyboard = Mock()
        mock_page.keyboard.insert_text = Mock()

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 0

        result = action._execute(mock_page)

        # Verify navigation was attempted
        mock_page.goto.assert_called_once_with(
            'https://tikvid.io/vi',
            wait_until="domcontentloaded",
            timeout=60000
        )
        assert result == mock_page

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_already_on_tikvid(self, action):
        """Test execution when already on TikVid page."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()

        # Mock all the interaction methods
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))
        mock_page.keyboard = Mock()
        mock_page.keyboard.insert_text = Mock()

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 0

        result = action._execute(mock_page)

        # Verify navigation was not attempted
        mock_page.goto.assert_not_called()
        assert result == mock_page

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_field_fill_success(self, action):
        """Test successful field filling."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock successful field interaction
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))

        # Mock button clicking
        mock_button = Mock()
        mock_button.click = Mock()
        mock_page.get_by_role = Mock(return_value=mock_button)
        mock_page.keyboard = Mock()
        mock_page.press = Mock(return_value=None)  # First strategy fails

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 0

        result = action._execute(mock_page)

        # Verify field was filled
        mock_field.click.assert_called()
        mock_field.fill.assert_any_call("")
        mock_field.fill.assert_any_call(action.tiktok_url)

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_field_fill_fallback_keyboard(self, action):
        """Test field filling fallback to keyboard insertion."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock field interaction where fill fails
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock(side_effect=[Exception("Fill failed"), None])
        mock_page.locator = Mock(return_value=Mock(first=mock_field))
        mock_page.keyboard = Mock()
        mock_page.keyboard.insert_text = Mock()

        # Mock button clicking
        mock_page.press = Mock(return_value=None)  # First strategy fails
        mock_page.get_by_role = Mock(return_value=Mock(click=Mock()))

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 0

        result = action._execute(mock_page)

        # Verify keyboard insertion was used as fallback
        mock_page.keyboard.insert_text.assert_called_once_with(action.tiktok_url)

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_button_click_strategies(self, action):
        """Test multiple button click strategies."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock field interaction
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))

        # Mock button clicking - first two strategies fail, third succeeds
        call_count = 0
        def mock_click_strategy():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Strategy {call_count} failed")
            return None

        mock_page.press = Mock(side_effect=mock_click_strategy)
        mock_page.get_by_role = Mock(side_effect=mock_click_strategy)
        mock_button = Mock()
        mock_button.click = Mock()
        mock_page.locator.return_value = Mock(first=mock_button)

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()
        mock_page.locator.return_value.count.return_value = 0

        result = action._execute(mock_page)

        # Verify multiple strategies were tried
        assert call_count == 3
        mock_page.press.assert_called_once_with("Enter")
        mock_page.get_by_role.assert_called_once_with("button", name="Download")

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_no_click_strategy_works(self, action):
        """Test when no click strategy works."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock field interaction
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))

        # Mock all button click strategies failing
        def mock_failing_strategy():
            raise Exception("All strategies fail")

        mock_page.press = Mock(side_effect=mock_failing_strategy)
        mock_page.get_by_role = Mock(side_effect=mock_failing_strategy)
        mock_page.locator.return_value.first.click = Mock(side_effect=mock_failing_strategy)

        with pytest.raises(Exception, match="Could not click download button"):
            action._execute(mock_page)

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_link_extraction_success(self, action):
        """Test successful link extraction."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock field and button interactions
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))
        mock_page.press = Mock()

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()

        # Mock link extraction
        mock_link1 = Mock()
        mock_link1.get_attribute = Mock(return_value="/video.mp4")
        mock_link2 = Mock()
        mock_link2.get_attribute = Mock(return_value="https://example.com/absolute.mp4")

        mock_locator = Mock()
        mock_locator.count.return_value = 2
        mock_locator.nth = Mock(side_effect=[mock_link1, mock_link2])
        mock_page.locator.return_value = mock_locator

        # Mock URL evaluation
        mock_page.evaluate = Mock(side_effect=[
            "https://tikvid.io/vi/video.mp4",  # First link resolved to absolute
            "https://example.com/absolute.mp4",  # Second link already absolute
        ])

        result = action._execute(mock_page)

        # Verify links were extracted
        assert len(action.result_links) == 2
        assert "https://tikvid.io/vi/video.mp4" in action.result_links
        assert "https://example.com/absolute.mp4" in action.result_links

    @patch('app.services.tiktok.download.actions.resolver.TIKVID_BASE', 'https://tikvid.io/vi')
    def test_execute_link_extraction_with_selectors(self, action):
        """Test link extraction with multiple selectors."""
        mock_page = Mock()
        mock_page.url = "https://tikvid.io/vi"
        mock_page.wait_for_load_state = Mock()

        # Mock field and button interactions
        mock_field = Mock()
        mock_field.click = Mock()
        mock_field.fill = Mock()
        mock_page.locator = Mock(return_value=Mock(first=mock_field))
        mock_page.press = Mock()

        mock_page.wait_for_function = Mock()
        mock_page.wait_for_timeout = Mock()

        # Mock multiple selectors - first selector fails, second succeeds
        mock_link = Mock()
        mock_link.get_attribute = Mock(return_value="https://example.com/video.mp4")

        def mock_locator_side_effect(selector):
            if selector == "a:has-text('Download MP4')":
                # First selector - no links found
                mock_locator = Mock()
                mock_locator.count.return_value = 0
                return mock_locator
            elif selector == "a[href*='mp4']":
                # Second selector - found link
                mock_locator = Mock()
                mock_locator.count.return_value = 1
                mock_locator.nth = Mock(return_value=mock_link)
                return mock_locator
            else:
                return Mock(count=Mock(return_value=0))

        mock_page.locator.side_effect = mock_locator_side_effect
        mock_page.evaluate = Mock(return_value="https://example.com/video.mp4")

        result = action._execute(mock_page)

        # Verify link was found with second selector
        assert len(action.result_links) == 1
        assert action.result_links[0] == "https://example.com/video.mp4"

        # Verify both selectors were tried
        assert mock_page.locator.call_count >= 2