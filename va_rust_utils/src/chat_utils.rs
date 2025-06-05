//! `python后端chat_utils模块扩展`
//!
//! `处理引用文件、上传图片、工具调用排版`
//!
//! # Examples
//! ```rust
//! use crate::file_utils::{attachment_processor, tool_formatter};
//! attachment_processor::process_attachments("帮我看一下代码和依赖", ["code.py", "requirements.txt"]);
//! tool_formatter::format_tools(r#"{ \n "tool_name": \n "arg_name""#);
//! ```
pub mod attachment_processor;
pub mod media_handler;
// pub mod tool_formatter;
