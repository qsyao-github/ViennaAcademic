use pyo3::prelude::*;

mod academic_utils {
    pub mod paper;
}
use crate::academic_utils::paper::academic_utils_paper_attach;
use crate::academic_utils::paper::academic_utils_paper_chunk;
use crate::academic_utils::paper::LINEBREAK_RE;
use crate::academic_utils::paper::SUFFIX_MAP;

mod chat_utils {
    pub mod attachment_processor;
    pub mod tool_formatter;
}
use crate::chat_utils::attachment_processor::chat_utils_attachment_processor_process_attachments;
use crate::chat_utils::attachment_processor::ATTACH_RE;
use crate::chat_utils::tool_formatter::chat_utils_tool_formatter_format_tools;
use crate::chat_utils::tool_formatter::TOOL_CALL_PATTERN;

mod file_utils {
    pub mod file_conversion;
}
use crate::file_utils::file_conversion::file_utils_file_conversion_markdown_to_everything;
use crate::file_utils::file_conversion::REMOVE_CITATION_PATTERN;

#[pyfunction]
fn initialize_static() {
    LINEBREAK_RE.split("Line1  \n\n  Line2");
    SUFFIX_MAP.get("py");
    ATTACH_RE.replace_all("#attach{some text}", "");
    TOOL_CALL_PATTERN.replace_all(r#"{ \n "tool_name": \n "arg_name""#, "");
    REMOVE_CITATION_PATTERN.replace_all("#cite(some text)", "");
}

#[pymodule]
fn va_rust_utils(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(initialize_static, m)?)?;
    m.add_function(wrap_pyfunction!(academic_utils_paper_attach, m)?)?;
    m.add_function(wrap_pyfunction!(academic_utils_paper_chunk, m)?)?;
    m.add_function(wrap_pyfunction!(
        chat_utils_attachment_processor_process_attachments,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(chat_utils_tool_formatter_format_tools, m)?)?;
    m.add_function(wrap_pyfunction!(
        file_utils_file_conversion_markdown_to_everything,
        m
    )?)?;
    Ok(())
}
