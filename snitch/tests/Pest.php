<?php

use Tests\SnitchFeatureTestCase;
use Tests\TestCase;

pest()->extend(TestCase::class)->in('Feature/ExampleTest.php');

pest()->extend(SnitchFeatureTestCase::class)->in('Feature/Snitch');
