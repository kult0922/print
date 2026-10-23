// Units: mm. Printable parts share one source and the same socket transform.
// openscad -D 'part="card"' -o output/card.stl models/nikko_trophy.scad
part = "assembly"; // "card", "base", "fit_test", "text_test", "assembly"
$fn = 64;
card_w = 63;
card_h = 88;
card_t = 3;
card_r = 3.5;
relief = 0.8;
clearance = 0.25; // PER SIDE; slot thickness = card_t + 2*clearance
lean_side = 18;
lean_back = 10;
insertion = 10;
base_h = 32;
label_lines = [
    // text, size, vertical center, tracking, extra stroke thickness per side
    ["RSOP Season 6 Champion", 4, 27, 1.04, 0],
    ["Nikko", 8, 18.5, 1.04, 0],
    ["2026/04-10", 3.8, 10.7, 1.10, 0.06]
];
// A print-flat card occupies x/y, with the decorated face toward +z.
// In the assembly it faces -y. The bottom-left corner is inserted.
corner_low = -(card_w/2*sin(lean_side) + card_h/2*cos(lean_side))
             + card_r*(sin(lean_side)+cos(lean_side)-1);
card_lift = base_h - insertion - cos(lean_back)*corner_low;
card_y = 9;

module rounded_rect(w,h,r) {
    offset(r=r) square([w-2*r,h-2*r], center=true);
}

module spade_2d(size) {
    // Pointed crown, two rounded lobes, and a broad connected stem.
    scale([size/24,size/28]) union() {
        polygon([[0,14],[-10,3],[10,3]]);
        translate([-5,-0.5]) circle(r=7);
        translate([5,-0.5]) circle(r=7);
        polygon([[-1.8,-3],[1.8,-3],[2.4,-9],[5,-13],[-5,-13],[-2.4,-9]]);
    }
}

module corner_index() {
    translate([-23,30,card_t-0.01]) linear_extrude(relief+0.01)
        text("A",size=10.5,font="DejaVu Serif:style=Bold",halign="center",valign="center");
    translate([-23,18.5,card_t-0.01]) linear_extrude(relief+0.01) spade_2d(8.5);
}

module card() {
    union() {
        linear_extrude(card_t) rounded_rect(card_w,card_h,card_r);
        translate([0,0,card_t-0.01]) linear_extrude(relief+0.01) spade_2d(29);
        corner_index();
        rotate([0,0,180]) corner_index();
    }
}

module mounted_card() {
    translate([0,card_y,card_lift])
        rotate([-lean_back,0,0]) rotate([0,-lean_side,0]) rotate([90,0,0])
            children();
}

module socket() {
    mounted_card() translate([0,0,-clearance])
        linear_extrude(card_t+2*clearance)
            offset(delta=clearance) rounded_rect(card_w,card_h,card_r);
}

module beveled_body(w,d,h,r,bevel) {
    hull() {
        linear_extrude(0.01) rounded_rect(w-2*bevel,d-2*bevel,r-bevel);
        translate([0,0,bevel]) linear_extrude(h-2*bevel)
            rounded_rect(w,d,r);
        translate([0,0,h-0.01]) linear_extrude(0.01)
            rounded_rect(w-2*bevel,d-2*bevel,r-bevel);
    }
}

module engraving(face_y=-32, z_offset=0) {
    // Same geometry and print orientation on the base and the text sample.
    // 0.8 mm deep engraving; slightly more tracking for readable small text.
    for (line = label_lines)
        translate([0,face_y+0.8,line[2]+z_offset]) rotate([90,0,0]) linear_extrude(1)
            offset(delta=line[4])
                text(line[0],size=line[1],spacing=line[3],font="DejaVu Sans:style=Bold",halign="center",valign="center");
}

module base() {
    difference() {
        union() {
            beveled_body(100,70,6,9,1);
            translate([0,0,6]) beveled_body(94,64,base_h-6,7,1.2);
        }
        socket();
        engraving();
    }
}

module fit_test() {
    // Same real socket and insertion depth; reduce the surrounding plinth.
    translate([0,0,-(base_h-14)]) difference() {
        translate([0,0,base_h-14]) linear_extrude(14) rounded_rect(60,30,4);
        socket();
    }
}

module text_test() {
    // Small upright sample: same text size, depth and layer direction as base.
    difference() {
        translate([-45,-4,0]) cube([90,8,26]);
        engraving(face_y=-4,z_offset=-6);
    }
}

if (part == "card") card();
else if (part == "base") base();
else if (part == "fit_test") fit_test();
else if (part == "text_test") text_test();
else if (part == "assembly") {
    color([0.56,0.32,0.09]) base();
    color([0.95,0.92,0.82]) mounted_card() card();
}
else assert(false,"Unknown part");
