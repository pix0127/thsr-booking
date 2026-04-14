# -*- coding: utf-8 -*-
"""
CLI 模組單元測試
測試 InteractiveCLIController 的 parse_args 和 show_output 方法
"""
import pytest
from io import StringIO
from controller.interactive_menu import InteractiveCLIController


class TestInteractiveCLIController:
    @pytest.fixture
    def controller(self):
        return InteractiveCLIController()

    # parse_args tests
    def test_parse_args_empty(self, controller):
        result = controller.parse_args([])
        assert result == {}

    def test_parse_args_create(self, controller):
        result = controller.parse_args(["create"])
        assert result == {"command": "create_reservation"}

    def test_parse_args_execute(self, controller):
        result = controller.parse_args(["execute"])
        assert result == {"command": "execute_reservations"}

    def test_parse_args_list(self, controller):
        result = controller.parse_args(["list"])
        assert result == {"command": "list_reservations"}

    def test_parse_args_delete(self, controller):
        result = controller.parse_args(["delete"])
        assert result == {"command": "delete_reservation"}

    def test_parse_args_help(self, controller):
        result = controller.parse_args(["help"])
        assert result == {"command": "help"}

    def test_parse_args_unknown(self, controller):
        result = controller.parse_args(["unknown_cmd"])
        assert result == {"command": "interactive"}

    # show_output tests
    def test_show_output_success(self, controller, capsys):
        controller.show_output({"success": "Test success"})
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "Test success" in captured.out

    def test_show_output_error(self, controller, capsys):
        controller.show_output({"error": "Test error"})
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "Test error" in captured.out

    def test_show_output_message(self, controller, capsys):
        controller.show_output({"message": "Test message"})
        captured = capsys.readouterr()
        assert "💡" in captured.out
        assert "Test message" in captured.out

    def test_show_output_string(self, controller, capsys):
        controller.show_output("plain string")
        captured = capsys.readouterr()
        assert "plain string" in captured.out

    # execute_command_mode tests
    def test_execute_command_mode_unknown(self, controller):
        result = controller._execute_command_mode({"command": "unknown"})
        assert "error" in result
        assert "未知命令" in result["error"]

    def test_execute_command_mode_delete_needs_id(self, controller):
        result = controller._execute_command_mode({"command": "delete_reservation"})
        assert "error" in result
        assert "需要指定預約 ID" in result["error"]
