/*
alert("whats up");
console.log("what's up?");
*/

function updateSparklines(width, height) {
  var sparklineItems = document.getElementsByClassName("sparkline");
  [].forEach.call(sparklineItems, function (el) {
    var el_id = el.id;
    var pvName = el_id.substring(el_id.indexOf("-")+1, el_id.length);
    var pvName = pvName.replace(/-COLON-/g, ':').replace(/-DOT-/g, '.');

    var sparklineChart = sparkline()
                         .width(width)
                         .height(height)
                         .gradientColors(['green', 'orange', 'red']) // OK, WARNING, ALARM
                         .dataSource('/api/history/' + pvName)
                         .dataSourceType('JSON')
                         .selector('#'+el.id);
    sparklineChart();  // render the chart
  });
};


function copyToClipboard(text, el) {
  // COPY TO CLIPBOARD
  // Attempts to use .execCommand('copy') on a created text field
  // Falls back to a selectable alert if not supported
  // Attempts to display status in Bootstrap tooltip
  // ------------------------------------------------------------------------------
  var copyTest = document.queryCommandSupported('copy');
  var elOriginalText = el.attr('data-original-title');

  if (copyTest === true) {
    var copyTextArea = document.createElement("textarea");
    copyTextArea.value = text;
    document.body.appendChild(copyTextArea);
    copyTextArea.select();
    try {
      var successful = document.execCommand('copy');
      var msg = successful ? 'Copied!' : 'Whoops, not copied!';
      el.attr('data-original-title', msg).tooltip('show');
    } catch (err) {
      console.log('Oops, unable to copy');
    }
    document.body.removeChild(copyTextArea);
    el.attr('data-original-title', elOriginalText);
  } else {
    // Fallback if browser doesn't support .execCommand('copy')
    window.prompt("Copy to clipboard: Ctrl+C or Command+C, Enter", text);
  }
}
