function toggleAnswer() {
  var front = document.getElementById('card-front');
  var back = document.getElementById('card-back');
  if (!front || !back) return;
  front.classList.toggle('d-none');
  back.classList.toggle('d-none');
}