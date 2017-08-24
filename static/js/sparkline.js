// https://github.com/DKirwan/reusable-d3-sparkline/blob/master/sparkline.js

// Built to closely follow reusable charts best practices doc: http://bost.ocks.org/mike/chart/

var parseDate = d3.time.format("%d-%b-%y").parse,
    bisectDate = d3.bisector(function(d) { return d[0]; }).left,
    formatValue = d3.format(",.3f");

function sparkline() {
  // defaults
  var width = 200;
  var height = 40;
  var dataSource = '';
  var dataSourceType = '';
  var selector = 'body';
  var gradientColors = ['green', 'orange', 'red'];

  // setters and getters
  chart.width = function(value) {
    if (!arguments.length) return width;
    width = value;
    return chart;
  };

  chart.height = function(value) {
    if (!arguments.length) return height;
    height = value;
    return chart;
  };

  chart.dataSource = function(value) {
    if (!arguments.length) return dataSource;
    dataSource = value;
    return chart;
  };

  chart.dataSourceType = function(value) {
    if (!arguments.length) return dataSourceType;
    dataSourceType = value;
    return chart;
  };

  chart.selector = function(value) {
    if (!arguments.length) return selector;
    selector = value;
    return chart;
  };

  chart.gradientColors = function(value) {
    if (!arguments.length) return gradientColors;
    gradientColors = value;
    return chart;
  };

  // chart setup
  function chart() {
    var margin = {
      top: 5,
      right: 5,
      bottom: 5,
      left: 5
    };

    var width = chart.width();
    var height = chart.height();
    var gradient;

    var x = d3.time.scale().range([0, width]);
    var y = d3.scale.linear().range([height, 0]);

    // Define the line
    var valueline = d3.svg.line()
      .x(function (d) { return x(d[0]); })
      .y(function (d) { return y(d[1]); });

    // Adds the svg canvas to the selector - 'body' by default
    var svg = d3.select(chart.selector())
      .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
      .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    if (chart.gradientColors() && chart.gradientColors().length) {
      // this defines the gradient used
      gradient = svg.append("defs")
        .append("linearGradient")
          .attr("id", "gradient")
          .attr("x1", "0%")   // starting x point
          .attr("y1", "0%")   // starting y point
          .attr("x2", "0%")   // ending x point
          .attr("y2", "100%") // ending y point
          .attr("spreadMethod", "pad");

      chart.gradientColors().forEach(function (color, index) {
        gradient.append("stop")
          .attr("offset", ((index * 100) / chart.gradientColors().length) + '%')
          .attr("stop-color", color)
          .attr("stop-opacity", 0.7);
      })
    }

    if (chart.dataSourceType().toLowerCase() === 'csv') {
      d3.csv(chart.dataSource(), drawChart);
    } else if (chart.dataSourceType().toLowerCase() === 'tsv') {
      d3.tsv(chart.dataSource(), drawChart);
    } else {
      d3.json(chart.dataSource(), function(error, json) {
        if (error) return drawChart(error, json);
        drawChart(error, json.history);
      });
    }

    /*
    * formats chart data and appends the sparkline
    */
    function drawChart(error, data) {
      if (error) { console.log(error); return; }

      data.forEach(function (d) {
        d[0] = new Date(d[0]);
        d[1] = +d[1];
      });

      // Scale the range of the data
      x.domain(d3.extent(data, function (d) { return d[0]; }));
      y.domain(d3.extent(data, function (d) { return d[1]; }));


      // Add the valueline path.
      svg.append('path')
        .attr('class', 'line')
        .attr('stroke', function () {
          if (gradient) {
            return 'url(#gradient)';
          }
          return '#444444';
        })
        .attr('d', valueline(data));

      var tooltip =   svg.append("text")
            .attr("x", 9)
            //.attr("dy", ".35em");
            .attr("y", height/2)
            //.style("z-index", "10")
            .text("");
            //.text("- value -");
            
      var focus = svg.append("g")
          .attr("class", "focus")
          .style("display", "none");

      focus.append("circle")
          .attr("r", 4.5);

      svg.append("rect")
          .attr("class", "overlay")
          .attr("width", width)
          .attr("height", height)
          .on("mouseover", function() { focus.style("display", null); })
          .on("mouseout", function() { focus.style("display", "none"); tooltip.text("");})
          .on("mousemove", mousemove);

      function mousemove() {
        var x0 = x.invert(d3.mouse(this)[0]),
            i = bisectDate(data, x0, 1),
            d0 = data[i - 1],
            d1 = data[i];
        //console.log(d3.mouse(this)[0]);
        //console.log(d3.mouse(this)[1]);
        var d = x0 - d0[0] > d1[0] - x0 ? d1 : d0;
        //console.log(x(d[0]));
        //console.log(y(d[1]));
        focus.attr("transform", "translate(" + x(d[0]) + "," + y(d[1]) + ")");
        tooltip.text(d[1]);
      }
    }
  }

  return chart;
}
