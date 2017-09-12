/*
alert("whats up");
console.log("what's up?");
*/

function updateSparklines() {
  var sparklineItems = document.getElementsByClassName("sparkline");
  [].forEach.call(sparklineItems, function (el) {
    var el_id = el.id;
    var pvName = el_id.substring(el_id.indexOf("-")+1, el_id.length);
    var pvName = pvName.replace(/-/g, ':');

    var sparklineChart = sparkline()
                         .width(155)
                         .height(50)
                         .gradientColors(['green', 'orange', 'red']) // OK, WARNING, ALARM
                         .dataSource('/api/history/' + pvName + '.json')
                         .dataSourceType('JSON')
                         .selector('#'+el.id);
    sparklineChart();  // render the chart
  });
};
