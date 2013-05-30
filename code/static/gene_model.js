var created = false;
var protein_scale = null;
var color_scale = null;
var gVariants = null;
var gDomains = null;
PLOT_FEATURES = ["DOMAIN","DNA_BIND","TRANSMEM","CA_BIND","ZN_BIND","NA_BIND","MOTIF"]


function draw_variant(selection, aa_pos){
    height = 35
    aa_pos = parseFloat(aa_pos);
    marker = selection.append("g").attr("class", "variant")
    marker.append("line").
        attr("x1", function (d){return protein_scale(aa_pos)}).
        attr("x2", function (d){return protein_scale(aa_pos)}).
        attr("y1", 120).
        attr("y2", 120-height).
        attr("stroke-width", 2).
        attr("stroke", "red")
    marker.append("circle").
        attr("cx", function (d){return protein_scale(aa_pos)}).
        attr("cy", 120-height).
        attr("r", 5).
        attr("fill", "red")
}

function draw_variants(data){
    gVariants.selectAll(".variant").remove();
     for (var i = 0; i < data.length; i++){
        gVariants.call(draw_variant, data[i]);
    }
}

function draw_domain(selection){
    selection.append("rect").
        attr("class", "domain").
        attr("x", function (d){return protein_scale(d.start)}).
        attr("y", 100).
        attr("height", 40).
        attr("width", function(d){return protein_scale(d.stop-d.start)}).
        attr("fill", function(d,i){return color_scale(PLOT_FEATURES.indexOf(d.type));});
    // selection.append("line").
    //     attr("x1", function (d){return protein_scale(d.start)}).
    //     attr("x2", function (d){return protein_scale(d.stop)}).
    //     attr("y1", 143).
    //     attr("y2", 143).
    //     attr("stroke-width", 2).
    //     attr("stroke", "blue")
       selection.append("title").
        attr("class", "domain_label").
        attr("x", function (d){return protein_scale(((d.stop-d.start)/2)+d.start)}).
        attr("y", 160).
        attr("text-anchor", "middle").
        text(function (d){return d.name ;});
}

function draw_model(gene_model, data, aa_length){
    svg_el_width = gene_model[0]["0"].clientWidth
    protein_scale = d3.scale.linear().domain([0, aa_length]).range([0, svg_el_width]);
    color_scale = d3.scale.category10()
    if (created){
        gVariants.remove();
        gDomains.remove();
        gene_model.selectAll("line").remove();

    }
    gVariants = gene_model.append("g").attr("id","variants")
    //draw_variants();

    gene_model.append("line").
        attr("x1", 0).
        attr("x2", protein_scale(aa_length)).
        attr("y1", 120).
        attr("y2", 120).
        attr("stroke-width", 22).
        attr("stroke", "#CCC")
    
    gDomains =  gene_model.append("g").attr("id","domains")
    gDomains.selectAll("rect").
        data(data).
        enter().
        append("g").
        call(draw_domain);
    created = true;
}