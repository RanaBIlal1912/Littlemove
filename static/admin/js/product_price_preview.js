document.addEventListener("DOMContentLoaded", function () {
  var price = document.getElementById("id_price");
  var oldPrice = document.getElementById("id_compare_at_price");
  if (!price || !oldPrice) return;

  var preview = document.createElement("span");
  preview.id = "id_price_preview";
  preview.style.cssText = "margin-left:12px;color:#067647;font-weight:600;font-size:.9rem;vertical-align:middle";
  oldPrice.insertAdjacentElement("afterend", preview);

  function update() {
    var p = parseInt(price.value, 10);
    var op = parseInt(oldPrice.value, 10);
    if (op > p && p > 0 && op > 0) {
      var save = op - p;
      var pct = Math.round(save / op * 100);
      preview.textContent = "→ Save Rs " + save.toLocaleString() + " (" + pct + "% off)";
    } else {
      preview.textContent = "";
    }
  }

  price.addEventListener("input", update);
  oldPrice.addEventListener("input", update);
  update();
});
