$('#delete-film-modal').on('show.bs.modal', function (event) {
  let url = event.relatedTarget.dataset.url;
  let form = this.querySelector('form');
  let filmName = event.relatedTarget.closest('tr').querySelector('.film-name').textContent;
  form.action = url;
  this.querySelector('#film-name').textContent = filmName;
})

$('select').selectpicker();