app=angular.module('app', []);

app.controller('main', function($scope,$http,$interval) {
	var ROOT_PATH="/backend/";
	$scope.list=[];
	$scope.book="";
	$scope.extension="";

	$scope.activeTab = 'SEARCH';
	$scope.getList = function() {
		$http.get(ROOT_PATH).then(
		function(data) {
			/*
			data.data=data.data.map(function(el) {
				if (el.STATUS!="DISCONNECTED")
					el.STATUS=el.STATUS+" "+el.ELAPSED;
				return el;
			});
			*/
			$scope.list=data.data;
		},
		function(data){
			console.log("error");

		});
	}
	$scope.getList();

	$scope.download = function(book) {
		$http.post(ROOT_PATH+"?adasasd",{"type":"BOOK","book":book}).then(
		function(data) {
			$scope.newElement(true);
			$scope.getList();
		},
		function(data){
			console.log("error");
			console.log(data);
		});
	};

	$scope.newElement = function(bool){
		$scope.new = bool;
	}
	$scope.searchBook = function(book,extension){
		$http.post(ROOT_PATH+"?ewqewqewq", {"type":"search","book":book,"extension":extension}).then(
		function(data) {
			console.log("success");
			$scope.getList();
		},
		function(data){
			console.log("err");
		});
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
	$interval($scope.getList, 3500);
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
