import os
import datetime
import glob
import subprocess
import gradio as gr
from typing import Generator, Dict, List, Union, Tuple, Callable
from chat import ChatManager, ContentProcessor

LATEX_DELIMITERS = [{
    'left': '$$',
    'right': '$$',
    'display': True
}, {
    'left': '$',
    'right': '$',
    'display': False
}]





def check_delete(current_user: str) -> None:
    for file_path in glob.glob("*.png"):
        os.remove(file_path)
    subprocess.run(f'find {current_user} -type f -mtime +2 -exec rm {{}} \\;',
                   shell=True)


def exclusive_switch(main_switch: bool, secondary_switch: bool) -> bool:
    if main_switch:
        secondary_switch = False
    return secondary_switch


def append_text(chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
                text: str, message_type: str) -> None:
    chatbot.append({
        "role": message_type,
        "metadata": None,
        "content": text,
        "options": None
    })


def append_file(chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
                file_path: str, message_type: str) -> None:
    chatbot.append({"role": message_type, "content": {"path": file_path}})


def append_files(chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
                 file_paths: List[str], message_type: str) -> None:
    for file_path in file_paths:
        append_file(chatbot, file_path, message_type)


def respond(
    msg: Dict[str, Union[str, List[str]]],
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    multimodal_switch: bool, knowledgeBase_switch: bool, current_user_dir: str
) -> Generator[Tuple[Dict[str, Union[str, List[str]]], List[Dict[str, Union[
        str, Dict[str, str], None]]]], None, None]:

    # Main processing logic
    now_time = datetime.datetime.now().strftime('%y%m%d%H%M%S')
    possible_media_filename = f'{now_time}.png'

    # Process incoming message
    # A special suffix is added to formatted_text. This is to address gradio issue #10450
    formatted_text = ContentProcessor.format_formula(
        ContentProcessor.process_attachments(msg["text"], current_user_dir))
    append_text(chatbot, f'{formatted_text}\n$$ $$', 'user')
    append_files(chatbot, msg["files"], 'user')

    append_text(chatbot, '', 'assistant')

    # Generate and stream responses
    bot_response = ChatManager.stream_response(formatted_text, msg["files"],
                                               str(chatbot[0]),
                                               multimodal_switch, now_time)

    for response_chunk in bot_response:
        chatbot[-1]["content"] = response_chunk
        yield {"text": "", "files": []}, chatbot
    # same suffix for #10450
    chatbot[-1]["content"] += '\n$$ $$'

    # Handle generated media file if exists
    if os.path.exists(possible_media_filename):
        append_file(chatbot, possible_media_filename, 'assistant')

    yield {"text": "", "files": []}, chatbot


def search(
    focus_mode: str
) -> Callable[[str, List[Dict[str, Union[str, Dict[str, str], None]]]],
              Generator[Tuple[str, List[Dict[str, Union[str, Dict[str, str],
                                                        None]]]], None, None]]:

    def _search(
        query: str, chatbot: List[Dict[str, Union[str, Dict[str, str], None]]]
    ) -> Generator[Tuple[str, List[Dict[str, Union[str, Dict[str, str],
                                                   None]]]], None, None]:
        append_text(chatbot, f'请搜索{query}', 'user')
        yield "", chatbot
        append_text(
            chatbot,
            ChatManager.append_search_result(query, focus_mode,
                                             str(chatbot[0])), 'assistant')
        yield "", chatbot

    return _search
