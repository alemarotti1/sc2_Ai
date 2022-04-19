
var canvas = document.getElementById("canvas")
canvas.width = window.innerWidth-100;
canvas.height = window.innerHeight-100;

var context = canvas.getContext("2d");



var mousePos = {
	x: null,
	y: null
}



function ponto(x, y, c){
	var radius = 10
	c.beginPath();
	
	
	c.arc(x,y,radius,0,2*Math.PI, true);
	c.fill();
}

function linha(x, y, x2, y2, c){
	c.beginPath();
	c.moveTo(x,y);
	c.lineTo(x2,y2);
	c.stroke();
}
function clear(c){
	c.clearRect(0, 0, canvas.width, canvas.height);
}

function curve(){
	this.pontos_controle = [];
	
	
	this.draw = function(c, color = null, control_point = true, control_pol = true, curve = true){
		if(this.pontos_controle.size!=0){
			if(color==null){
				c.strokeStyle = "black";
				c.fillStyle = "black";
			}
			else{
				c.strokeStyle = color;
				c.fillStyle = color;
			}
			if(control_point)this.drawControlPoints(c);
			if(control_pol) this.drawControlPolygon(c);
			if(curve)this.drawCurve(c);
		}
	}
	this.drawControlPoints = function(c){
		var lastPoint = null;
		for (x in this.pontos_controle){
			ponto(this.pontos_controle[x][0], this.pontos_controle[x][1], c);
		}
	}
	this.drawCurve = function(c){
		c.strokeStyle = 'red';
		var pontoCurva = [];
		var passos = Math.max(parseInt($("#passos").val()), 1);
		c.beginPath();
		for(t=0; t<=1; t = t+1/passos){
			var temp = this.pontos_controle;
				while(temp.length>1){
					var aux = [];
					for (x=0; x<temp.length-1; x++){
						var newX = (t)*temp[x][0]+(1-t)*temp[x+1][0];
						var newY = (t)*temp[x][1]+(1-t)*temp[x+1][1];
						//ponto(newX, newY, c);
						aux.push([newX, newY]);
					}
					temp = aux;
				}
				
				if(temp.length>0){ c.lineTo(temp[0][0], temp[0][1]);}
				pontoCurva.push(temp);
				//ponto(temp[0][0], temp[0][1], c)
		}
		c.stroke();
		console.log(pontoCurva);
	}
	this.drawControlPolygon = function(c){
		
		t=0.5;
		c.beginPath();
		var temp = this.pontos_controle;
		
		//c.strokeStyle = 'black';
		if(this.pontos_controle.length>1){
			var lastPoint = null;
			c.moveTo(this.pontos_controle[0][0], this.pontos_controle[0][1]);
			for (x in this.pontos_controle){
				if(lastPoint!=null) linha(lastPoint[0],lastPoint[1], this.pontos_controle[x][0], this.pontos_controle[x][1], c);
				lastPoint = this.pontos_controle[x];
			}	
		}
		c.stroke();
		c.beginPath();
		c.strokeStyle = 'orange';
		while(temp.length>1){
			
			
			var aux = [];
			for (x=0; x<temp.length-1; x++){
				var newX = (t)*temp[x][0]+(1-t)*temp[x+1][0];
				var newY = (t)*temp[x][1]+(1-t)*temp[x+1][1];
				c.lineTo(newX, newY);
				aux.push([newX, newY]);
			}
			temp = aux;
			c.moveTo(temp[0][0], temp[0][1])
		}

		c.stroke();
	}

	this.add_control = function(x,y){
			var point = [x, y]
			this.pontos_controle.push(point);
	}
	this.checkNDelete = function(x,y){
		var r = 15
		for(p in this.pontos_controle){
			var tempx = this.pontos_controle[p][0];var tempy = this.pontos_controle[p][1];
			if(x<tempx+r && x>tempx-r)
				if(y<tempy+r && y>tempy-r){
					this.pontos_controle.splice(p, 1);
					return true;
				}
		}
		return false;
	}
	
}

var ponto_c = true;
var pol_c = true;
var cur = true;

$(document).ready(function(){
	function remove(){
		$("#list").children().last().remove();
	}
	function updateList(){
		$("#list").append('<li class="active select"><a href="#section1">Selecionar Curva:'+(lista_curvas.length-1)+'</a></li>');
	}
	
	$("#add").click(function(){
		var temp = new curve();
		lista_curvas.push(temp);
		curva_ativa = lista_curvas.length-1;
		draw();
		alert 
		updateList();
		
		$(".select").click(function(){
		var temp = $(this).text();
		temp = temp.slice(17);
		temp = parseInt(temp);
		curva_ativa = temp;
		draw();
	});
		
	});
	$("#remove").click(function(){
		if(lista_curvas.length>0){
			remove();
			var temp = $("#rem_val").val();
			curva_ativa=0;
			lista_curvas.splice(temp,1);
			curva_ativa = lista_curvas.length-1;
			clear(context);
			draw(context, "black", ponto_c, pol_c, cur);
		}
	});
	
	$("#passos").change(function(){
		clear(context);
		draw(context, "black", ponto_c, pol_c, cur);
	});
	$("#ptct").click(function(){
		ponto_c = !ponto_c;
		clear(context);
		draw(context, "black", ponto_c, pol_c, cur);
	});
	$("#pol").click(function(){
		pol_c = !pol_c;
		clear(context);
		draw(context, "black", ponto_c, pol_c, cur);
	});
	$("#cur").click(function(){
		cur = !cur;
		clear(context);
		draw(context, "black", ponto_c, pol_c, cur);
	});
	
	
	
});

function draw(hightlight = -1){
	for(x in lista_curvas){
		if(x == curva_ativa) lista_curvas[x].draw(context, "green", ponto_c, pol_c, cur);
		else if(x == hightlight) lista_curvas[x].draw(context, "yellow", ponto_c, pol_c, cur);
		else lista_curvas[x].draw(context, "black", ponto_c, pol_c, cur);
	}
}
canvas.addEventListener("mousedown",function(event){
	if(event.button ==0) lista_curvas[curva_ativa].add_control(event.x, event.y);
	else lista_curvas[curva_ativa].checkNDelete(event.x, event.y);
	clear(context);
	draw();
	return false;
}, false);

var curva_ativa = 0;
var lista_curvas = [];
var bezier_curve = new curve();
lista_curvas.push(bezier_curve);



