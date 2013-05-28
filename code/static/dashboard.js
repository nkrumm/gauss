Array.prototype.max = function () {
  if (this.length > 1){
    return this.reduce(function (p, v) {
        return ( p > v ? p : v );
    });}
 else {return this}
}
Array.prototype.min = function () {
  return this.reduce(function (p, v) {
    return ( p < v ? p : v );
  });
}

function _max(d3_array){
    if (d3_array.length > 1){
        return d3.max(d3_array);
    } else{
        return d3_array;
    }
}
var dashboard = d3.select("#div-dashboard").
  append("svg:svg").
  attr("width", 600).
  attr("height", 600);

function title(selection, text) {
    selection.
    append("svg:text").
    attr("x", 5).
    attr("y", 20).
    attr("class", "title").
    text(text)
}

function score(selection, score) {
    selection.
    append("svg:text").
    attr("text-anchor", "end").
    attr("x", 95).
    attr("y", 95).
    attr("class", "score").
    text(score);
}

function scale_value(d){
    if (d["title"] in scales){
        return scales[d["title"]](_max(d["score"]));
    } else {
        return scales["default"]; 
    }
}

function label_value(d){
    if (d["title"] in label_scales){
        return label_scales[d["title"]](_max(d["score"])).split("\n").reverse();
    } else {
        return label_scales["default"]; 
    }
}

function square(selection) {
    selection.
    append("svg:rect").
    attr("x", 0).
    attr("y", 0).
    attr("rx", 4).
    attr("ry", 4).
    attr("height", 100).
    attr("width", 100).
    attr("fill", scale_value).
    attr("fill-opacity", 0.5);
}

function label(selection) {
    label_txt = selection.append("g");
    label_txt.selectAll("text").
        data(label_value).
        enter().
        append("text").
        attr("text-anchor", "end").
        attr("x", 95).
        attr("y", function(d,i){return 70 - i * 15}).
        attr("class", "dashboard-label").
        text(function(d){return d});
}

function format_score(score){
    
    if (score.length > 1){
        max = Math.round(score.min()*100)/100
        min = Math.round(score.max()*100)/100
        if (max != min){
            return  max + " – " + min;
        } else {
            return max;
        }
    }
    else{
        if (score == -999){
            return "";
        }
        else {
            return Math.round(score*1000)/1000;
        }
    }
}

function panel(selection) {
    selection.
    call(square).
    call(title, function(d) {return d["title"];}).
    call(score, function(d) {return format_score(d["score"]);}).
    call(label, function(d) {return d["score"];});
}

function multi_row(selection, title) {
    var g = selection.selectAll("g").
            data(function(d) {return d["freqs"];}).
            enter().append("g").
            attr("transform", function (d, i) {return "translate(0," + (42 + i * 30) + ")"})
    
    g.append("rect").
        attr("y", 0).
        attr("x", 0).
        attr("rx", 1).
        attr("ry", 1).
        attr("height", 28).
        attr("width", 100).
        attr("fill", function (d) {return scales["freq"](d["freq"])}).
        attr("fill-opacity", 0.5);

    g.append("svg:text").
        attr("x", 5).
        attr("y", 20).
        //attr("class", "title").
        text(function (d) {return d["pop"];})

    g.append("svg:text").
        attr("x", 95).
        attr("y", 20).
        attr("text-anchor", "end").
        attr("class", "freq").
        text(function (d) {return d["freq"];})

}
function multi_panel(selection) {
    selection.append("rect").
        attr("x", 0).
        attr("y", 0).
        attr("rx", 4).
        attr("ry", 4).
        attr("height", 38).
        attr("width", 100).     
        attr("fill", function (d) {return scales["freq"](d["overallfreq"])}).
        attr("fill-opacity", 0.5);

    selection.append("svg:text").
        attr("x", 3).
        attr("y", 20).
        attr("class", "title").
        text(function (d) {return d["title"];})
    selection.append("svg:text").
        attr("x", 95).
        attr("y", 32).
        attr("text-anchor", "end").
        attr("class", "freq large").
        text(function (d) {return d["overallfreq"];})

    selection.call(multi_row);
}

function hline(selection, y){
      selection.append("svg:line").
        attr("x1", 10).
        attr("x2", 800).
        attr("y1", y+0.5).
        attr("y2", y+0.5).
        attr("stroke", "black").
        attr("stroke-width", .25);
}

scales = {"GERPrs": d3.scale.threshold().domain([4]).range(["green","red"]),
          "P2hdiv": d3.scale.threshold().domain([-998, 0.452, 0.957]).range(["gray","green","orange","red"]),
          "SIFT": d3.scale.linear().domain([0,0.1,1]).range(["red", "green","green"]),
          "PyP": d3.scale.linear().domain([0,3]).range(["green", "red"]),
          "freq": d3.scale.linear().domain([0,0.1,1]).range(["red", "green","green"]),
          "FILTER": d3.scale.threshold().domain([0.5]).range(["green", "red"]),
          "default": "gray"}

label_scales = {"SIFT": d3.scale.threshold().domain([0.05]).range(["Damaging","Tolerated"]),
                "P2hdiv": d3.scale.threshold().domain([-998,0.452, 0.957]).range(["Not Tested", "Benign","Possibly\nDamaging","Probably\nDamaging"]),
                "FILTER": d3.scale.threshold().domain([0.5]).range(["", "NOT PASSING"]),
                "default": ""}


var default_scores = ["GERPrs", "SIFT", "PyP","P2hdiv","MTs","SLR"]

function make_dashboard(div, in_data, freq_data, GATK_data) {
    data = []
    in_data_titles = []
    $(in_data).each(function(index){in_data_titles.push(in_data[index]["title"])});

    $(default_scores).each(function (index){
        ds = default_scores[index]
        in_data_index = in_data_titles.indexOf(ds)
        if (in_data_index != -1){
            data.push(in_data[in_data_index])
        }
        else {
            data.push({"title": ds, "score": -999})
        }
    });

    dashboard = d3.select(div).
      append("svg:svg").
      attr("width", 800).
      attr("height", 450);

      dashboard.call(hline,1);
      dashboard.call(hline,120);
      dashboard.call(hline,300);
      row = dashboard.append("g").attr("id","scores");
      row.
        append("svg:text").
        attr("x", 130).
        attr("y", 30).
        attr("class","row-title").
        attr("text-anchor", "end").
        text("Impact");

      row.
        selectAll("g").
        data(data).
        enter().
        append("svg:g").
        attr("transform", function (d, i) {return "translate(" + (140 + i * 110) + ",10)";}).
        call(panel);

      row = dashboard.append("g").attr("id","frequencies");
      row.
        append("svg:text").
        attr("x", 130).
        attr("y", 40 + 110).
        attr("class","row-title").
        attr("text-anchor", "end").
        text("Frequency");

      row.
        selectAll("g").
        data(freq_data).
        enter().
        append("svg:g").
        attr("transform", function (d, i) {return "translate(" + (140 + i * 110) + ",130)";}).
        call(multi_panel);


      row = dashboard.append("g").attr("id","GATK");
      row.
        append("svg:text").
        attr("x", 130).
        attr("y", 330).
        attr("class","row-title").
        attr("text-anchor", "end").
        text("GATK");

      row.
        selectAll("g").
        data(GATK_data).
        enter().
        append("svg:g").
        attr("transform", function (d, i) {return "translate(" + (140 + i * 110) + ",310)";}).
        call(panel);
}


