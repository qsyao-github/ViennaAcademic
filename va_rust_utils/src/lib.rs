use pyo3::prelude::*;

mod academic_utils {
    pub mod paper;
}

#[pymodule]
fn va_rust_utils(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(
        academic_utils::paper::academic_utils_paper_chunk,
        m
    )?)?;
    Ok(())
}
