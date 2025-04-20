use pyo3::prelude::*;

mod academic_utils {
    pub mod paper;
}
use crate::academic_utils::paper::academic_utils_paper_attach;
use crate::academic_utils::paper::academic_utils_paper_chunk;

mod chat_utils {
    pub mod attachment_processor;
}
use crate::chat_utils::attachment_processor::chat_utils_attachment_processor_process_attachments;

#[pymodule]
fn va_rust_utils(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(academic_utils_paper_attach, m)?)?;
    m.add_function(wrap_pyfunction!(academic_utils_paper_chunk, m)?)?;
    m.add_function(wrap_pyfunction!(
        chat_utils_attachment_processor_process_attachments,
        m
    )?)?;
    Ok(())
}
