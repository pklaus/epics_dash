function updateStatus() {
  $.getJSON("/api/values.json")
    .fail(function( jqxhr, textStatus, error ) {
      var err = textStatus + ", " + error;
      console.log( "Request Failed: " + err );
    })
    .done(function( data ) {
      var gview = document.getElementById("gview");
      var svgDoc = gview.contentDocument;
      // ----------
      var svgItems = svgDoc.getElementsByClassName("dynamic");
      [].forEach.call(svgItems, function (el) {
        var el_id = el.id;
        var pvName  = el_id.substring(0, el_id.lastIndexOf("_"));
        var pvField = el_id.substring(el_id.lastIndexOf("_") + 1, el_id.length);
        var pvName = pvName.replace(/-/g, ':');
        var pv = data.PVs[data.PV_lookup[pvName]];
        if (pvField == "VAL")
          if (pv.value !== null && pv.precision !== null)
            el.textContent = pv.value.toFixed(pv.precision);
          else if (pv.value !== null)
            el.textContent = pv.value;
          else
            el.textContent = 'invalid';
        else if (pvField == "EGU")
          el.textContent = pv.unit;
      });
    });
};
