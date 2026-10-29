<?php

namespace App\Enums;

enum EpisodeType: string
{
    case MissingPpe = 'missing_ppe';
    case IdleZone = 'idle_zone';
    case Smartphone = 'smartphone';
}
