(() => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file');
  const fileNameEl = document.getElementById('file-name');
  const submitBtn = document.getElementById('submit-btn');

  function setFile(file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileNameEl.textContent = file.name;
    submitBtn.disabled = false;
  }

  if (dropzone) {
    ;['dragenter', 'dragover'].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('hover');
      });
    });

    ;['dragleave', 'drop'].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('hover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
          setFile(file);
        } else {
          alert('Veuillez déposer un fichier PDF.');
        }
      }
    });
  }

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      setFile(fileInput.files[0]);
    }
  });
})();


