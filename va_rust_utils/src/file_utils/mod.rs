//! `python后端file_utils模块扩展`
//!
//! `调用pandoc与typst完成格式转换`
//!
//! # Examples
//! ```rust
//! use crate::file_utils::file_conversion;
//! file_conversion::file_utils_file_conversion_pandoc_to_markdown("file", "path/to/file.pdf", "convert/to");
//! file_utils::file_utils_file_conversion_markdown_to_everything("path/to/file.md","convert/to","pdf");
//! ```
pub mod file_conversion;
