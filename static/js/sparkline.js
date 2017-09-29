// https://github.com/DKirwan/reusable-d3-sparkline/blob/master/sparkline.js

// Built to closely follow reusable charts best practices doc: http://bost.ocks.org/mike/chart/

var parseDate = d3.timeFormat("%d-%b-%y").parse,
    bisectDate = d3.bisector(function(d) { return d[0]; }).left,
    formatValue = d3.format(",.3f");

function sparkline() {
  // defaults
  var width = 200;
  var height = 40;
  var precision = null;
  var y_extent = null;
  var upper_disp_limit = null;
  var lower_disp_limit = null;
  var upper_warning_limit = null;
  var lower_warning_limit = null;
  var upper_alarm_limit = null;
  var lower_alarm_limit = null;
  var dataSource = '';
  var dataSourceType = '';
  var selector = 'body';
  var id = Math.floor(Math.random()*16777215).toString(16);
  var gradientColors = ['green', 'orange', 'red']; // OK, WARNING, ALARM
  var noGradientColor = '#333'; // Color to be use for charts if warning / alarm range not defined
  var gradient = null;

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

  chart.precision = function(value) {
    if (!arguments.length) return precision;
    precision = value;
    return chart;
  };

  chart.y_extent = function(value) {
    if (!arguments.length) return y_extent;
    y_extent = value;
    return chart;
  };

  chart.upper_disp_limit = function(value) {
    if (!arguments.length) return upper_disp_limit;
    upper_disp_limit = value;
    return chart;
  };

  chart.lower_disp_limit = function(value) {
    if (!arguments.length) return lower_disp_limit;
    lower_disp_limit = value;
    return chart;
  };

  chart.upper_warning_limit = function(value) {
    if (!arguments.length) return upper_warning_limit;
    upper_warning_limit = value;
    return chart;
  };

  chart.lower_warning_limit = function(value) {
    if (!arguments.length) return lower_warning_limit;
    lower_warning_limit = value;
    return chart;
  };

  chart.upper_alarm_limit = function(value) {
    if (!arguments.length) return upper_alarm_limit;
    upper_alarm_limit = value;
    return chart;
  };

  chart.lower_alarm_limit = function(value) {
    if (!arguments.length) return lower_alarm_limit;
    lower_alarm_limit = value;
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

  chart.noGradientColor = function(value) {
    if (!arguments.length) return noGradientColor;
    noGradientColor = value;
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

    var x = d3.scaleTime().range([0, width]);
    var y = d3.scaleLinear().range([height, 0]);

    // Define the line
    var valueline = d3.line()
      //.curve(d3.curveLinear)
      //.curve(d3.curveMonotoneX)
      .curve(d3.curveStepAfter)
      .defined(function (d) { return d[1] !== null; })
      .x(function (d) { return x(d[0]); })
      .y(function (d) { return y(d[1]); });

    // Adds the svg canvas to the selector - 'body' by default
    var svg = d3.select(chart.selector())
      .append('svg')
        .attr("viewBox", "0 0 " + (width + margin.left + margin.right) + " " + (height + margin.top + margin.bottom))
        .attr("preserveAspectRatio", "xMidYMid meet")
      .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');


    if (chart.dataSourceType().toLowerCase() === 'json') {
      d3.json(chart.dataSource(), function(error, json) {
        if (error) return drawChart(error, json);
        chart.precision(json.precision);
        chart.upper_disp_limit(json.upper_disp_limit);
        chart.lower_disp_limit(json.lower_disp_limit);
        chart.upper_warning_limit(json.upper_warning_limit);
        chart.lower_warning_limit(json.lower_warning_limit);
        chart.upper_alarm_limit(json.upper_alarm_limit);
        chart.lower_alarm_limit(json.lower_alarm_limit);
        calculateExtent(json.history);
        createGradient();
        drawChart(error, json.history);
      });
    }

    function calculateExtent(data) {
      if ((upper_disp_limit !== null) && (lower_disp_limit !== null))
        y_extent = [lower_disp_limit, upper_disp_limit];
      else {
        y_extent = d3.extent(data, function (d) { return d[1]; });
        if (y_extent[0] == y_extent[1]) y_extent = [ y_extent[0]-.5, y_extent[0]+.5];
      }
    }

    function createGradient() {
      var color;
      var upper_perc_offset = margin.top / (height + margin.top + margin.bottom) * 100;
      var lower_perc_offset = (margin.top + height) / (height + margin.top + margin.bottom) * 100;

      gradient = svg.append("defs")
        .append("linearGradient")
          .attr("id", "gradient"+id)
          .attr("x1", "0")   // starting x point
          .attr("y1", "0%")   // starting y point
          .attr("x2", "0")   // ending x point
          .attr("y2", height) // ending y point
          .attr("gradientUnits", "userSpaceOnUse")
          .attr("spreadMethod", "pad");
      if (upper_alarm_limit !== null) {
        perc_val = (upper_alarm_limit-upper_disp_limit)/(lower_disp_limit-upper_disp_limit)*100;
        gradient.append("stop")
          .attr("offset",  perc_val + '%')
          .attr("stop-color", gradientColors[2]) // ALARM color
          .attr("stop-opacity", 0.7);
        if (upper_warning_limit !== null)
          color = gradientColors[1]; // WARNING color
        else
          color = gradientColors[0]; // OK color
        gradient.append("stop")
          .attr("offset",  perc_val + '%')
          .attr("stop-color", color)
          .attr("stop-opacity", 0.7);
      }
      if (upper_warning_limit !== null) {
        perc_val = (upper_warning_limit-upper_disp_limit)/(lower_disp_limit-upper_disp_limit)*100;
        gradient.append("stop")
          .attr("offset", perc_val + '%')
          .attr("stop-color", gradientColors[1]) // WARNING color
          .attr("stop-opacity", 0.7);
        gradient.append("stop")
          .attr("offset", perc_val + '%')
          .attr("stop-color", gradientColors[0]) // OK color
          .attr("stop-opacity", 0.7);
      }
      color = null;
      if ((upper_alarm_limit === null) && (upper_warning_limit === null) && (lower_warning_limit === null) && (lower_alarm_limit === null)) {
        color = noGradientColor; // NO GRADIENT color
      } else if ((upper_alarm_limit === null) && (upper_warning_limit === null)) {
        color = gradientColors[0]; // OK color
      }
      if (color !== null)
        gradient.append("stop")
          .attr("offset", '0%')
          .attr("stop-color", color)
          .attr("stop-opacity", 0.7);
      if (lower_warning_limit !== null) {
        perc_val = (lower_warning_limit-upper_disp_limit)/(lower_disp_limit-upper_disp_limit)*100;
        gradient.append("stop")
          .attr("offset", perc_val + '%')
          .attr("stop-color", gradientColors[0]) // OK color
          .attr("stop-opacity", 0.7);
        gradient.append("stop")
          .attr("offset", perc_val + '%')
          .attr("stop-color", gradientColors[1]) // WARNING color
          .attr("stop-opacity", 0.7);
      }
      if (lower_alarm_limit !== null) {
        perc_val = (lower_alarm_limit-upper_disp_limit)/(lower_disp_limit-upper_disp_limit)*100;
        if (lower_warning_limit !== null)
          color = gradientColors[1]; // WARNING color
        else
          color = gradientColors[0]; // OK color
        gradient.append("stop")
          .attr("offset",  perc_val + '%')
          .attr("stop-color", color)
          .attr("stop-opacity", 0.7);
        gradient.append("stop")
          .attr("offset",  perc_val + '%')
          .attr("stop-color", gradientColors[2]) // ALARM color
          .attr("stop-opacity", 0.7);
      }
    }

    /*
    * formats chart data and appends the sparkline
    */
    function drawChart(error, data) {
      if (error) { console.log(error); return; }

      data.forEach(function (d) {
        d[0] = new Date(d[0] - (new Date().getTimezoneOffset()*60*1000));
        d[1] = d[1];
      });

      // Scale the range of the data
      x.domain(d3.extent(data, function (d) { return d[0]; }));
      y.domain(y_extent);


      // Add the valueline path.
      svg.append('path')
        .attr('class', 'line')
        .attr('stroke', function () {
          if (gradient) {
            return 'url(#gradient'+id+')';
          }
          return '#444444';
        })
        .attr('d', valueline(data));

      var tooltip_val =   svg.append("text")
            .attr("x", 9)
            //.attr("dy", ".35em");
            .attr("y", height*1/3)
            //.style("z-index", "10")
            .text("");
            //.text("- value -");

      var tooltip_ts =   svg.append("text")
            .attr("x", 9)
            .attr("y", height*2/3)
            .text("");

      var focus = svg.append("g")
          .attr("class", "focus")
          .attr("transform", "translate(-10,-10)")
          .style("display", "none");

      focus.append("circle")
          .attr("r", 4.5);

      svg.append("rect")
          .attr("class", "overlay")
          .attr("width", width)
          .attr("height", height)
          .on("mouseover", function() { focus.style("display", null); })
          .on("mouseout", function() {
            focus.style("display", "none");
            tooltip_val.text("");
            tooltip_ts.text("");
          })
          .on("mousemove", mousemove);

      function mousemove() {
        var x0 = x.invert(d3.mouse(this)[0]),
            i = bisectDate(data, x0, 0, data.length-2),
            d0 = data[Math.max(0, i - 1)],
            d1 = data[i];
        //console.log(d3.mouse(this)[0]);
        //console.log(d3.mouse(this)[1]);
        var d = x0 - d0[0] > d1[0] - x0 ? d1 : d0;
        //console.log(x(d[0]));
        //console.log(y(d[1]));
        var val = d[1];
        if (val != null && precision != null)
          val = val.toFixed(precision);
        if (val != null) {
          focus.attr("transform", "translate(" + x(d[0]) + "," + y(d[1]) + ")");
          tooltip_val.text(val);
          var iso_date = d[0].toISOString();
          tooltip_ts.text(iso_date.slice(11, 11+10));
        }
      }
    }
  }

  return chart;
}
