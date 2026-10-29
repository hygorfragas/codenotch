<?php

use Tests\SnitchFeatureTestCase;
use Tests\TestCase;

pest()->extend(TestCase::class)->in('Feature');

pest()->extend(SnitchFeatureTestCase::class)->in('Feature/Snitch');
