app=angular.module('app', []);

app.controller('main', function($scope,$http,$interval) {
	var ROOT_PATH="/backend/";
	$scope.searchlist=[]
	$scope.results = [];
	$scope.book="";
	$scope.extension="";

	$scope.activeTab = 'SEARCH';
    ws = new WebSocket("ws://192.168.1.12:8099/");
    ws.onmessage = function(event) {
        var j = JSON.parse(event.data);
        console.log(j);
        $scope.$apply(function() {
            $scope.searchlist=j['SEARCH'];
            $scope.results=j['BOOKS'];
        });
    };

	$scope.download = function(book) {
		ws.send(JSON.stringify({"type":"BOOK","book":book}));
    };

	$scope.newElement = function(bool){
		$scope.new = bool;
	}

	$scope.searchBook = function(book,extension){
		ws.send(JSON.stringify({"type":"search","book":book,"extension":extension}));
	};

	$scope.isActiveTab = function(tab){
		return $scope.activeTab === tab;
	}

	$scope.changeTab = function(tab){
		$scope.activeTab = tab;
	}

	$scope.limit = {};
	$scope.showMore = function(l){
		$scope.limit[l.ID] = $scope.limit[l.ID] ? undefined : l.OUT.length;
	}
    $scope.clean = function(s) {
        s = s.replace(/\(.*?\)/g, '');
        s.replace(/\s+/g, " ");
        s.replace(/\s+\./g, ".");
        return s;
    }
});

app.directive('progressBar', function(){
	return {
		template: '<div id="progress-bar"><div id="label">{{progress}}%</div><div id="progress" style="width:{{progress}}%"></div></div>',
		restrict: 'E',
		scope: {
			progress: '='
		},
		link: function(scope, elem, attrs){
			console.log('progress', scope.progress, elem, attrs);
		}
	}
});
